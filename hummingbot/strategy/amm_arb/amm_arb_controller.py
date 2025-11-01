import asyncio
import pandas as pd
from decimal import Decimal
from typing import List, Optional, Tuple

from hummingbot.client.performance import PerformanceMetrics
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.core.event.events import BuyOrderCompletedEvent, SellOrderCompletedEvent
from hummingbot.strategy.amm_arb.data_types import ArbProposal, ArbProposalSide
from hummingbot.strategy.amm_arb.utils import create_arb_proposals
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.v2.controllers.base_controller import BaseController
from hummingbot.strategy.v2.models.base import RunnableStatus
from hummingbot.strategy.v2.models.executor_info import ExecutorInfo

class AmmArbV2Controller(BaseController):
    """
    Controller for the AMM Arbitrage V2 strategy with dynamic order sizing.
    """

    def __init__(self, config, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.config = config
        self.last_proposal: Optional[ArbProposal] = None

    async def determine_actions(self) -> List[ExecutorInfo]:
        """
        Finds the optimal arbitrage opportunity and, if profitable, creates executors to execute the trades.
        """
        optimal_opportunity = await self.find_optimal_arb_opportunity()
        if not optimal_opportunity:
            return []

        proposal, profit_pct = optimal_opportunity
        self.last_proposal = proposal

        if profit_pct >= self.config.min_profitability:
            self.log_with_clock(
                f"Found profitable opportunity ({profit_pct:.2%}). "
                f"Executing trade with size {proposal.first_side.amount}."
            )
            return self.create_executors(proposal)
        return []

    async def find_optimal_arb_opportunity(self) -> Optional[Tuple[ArbProposal, Decimal]]:
        """
        Analyzes markets to find the trade size that maximizes profit percentage.
        Returns the best proposal and its profitability, or None if no opportunity exists.
        """
        market_1 = self.connectors["market_1"]
        market_2 = self.connectors["market_2"]

        # Check for opportunities: Buy on 1, Sell on 2 OR Buy on 2, Sell on 1
        opp1 = await self.find_best_size_for_direction(buy_market=market_1, sell_market=market_2)
        opp2 = await self.find_best_size_for_direction(buy_market=market_2, sell_market=market_1)

        # Return the opportunity with the highest profitability
        if opp1 and opp2:
            return opp1 if opp1[1] > opp2[1] else opp2
        return opp1 or opp2

    async def find_best_size_for_direction(self, buy_market: MarketTradingPairTuple, sell_market: MarketTradingPairTuple) -> Optional[Tuple[ArbProposal, Decimal]]:
        """
        Iterates through trade sizes to find the most profitable one for a given trade direction.
        """
        best_profit_pct = Decimal("-1")
        best_proposal = None
        
        # Iterate from min to max amount in steps to find the optimal size
        # A more advanced implementation might use a more sophisticated optimization algorithm
        num_steps = 20  # Number of sizes to check
        step_size = (self.config.max_order_amount - self.config.min_order_amount) / (num_steps - 1)

        for i in range(num_steps):
            order_amount = self.config.min_order_amount + i * step_size
            proposals = await create_arb_proposals(
                market_info_1=buy_market,
                market_info_2=sell_market,
                order_amount=order_amount,
            )
            
            # create_arb_proposals returns two proposals, we only care about one direction
            proposal = proposals[0] # The one that buys on market_info_1 and sells on market_info_2
            profit_pct = proposal.profit_pct(account_for_fee=True)

            if profit_pct > best_profit_pct:
                best_profit_pct = profit_pct
                best_proposal = proposal

        if best_proposal and best_profit_pct > 0:
            return best_proposal, best_profit_pct
        return None

    def create_executors(self, proposal: ArbProposal) -> List[ExecutorInfo]:
        """
        Creates executors for each side of the arbitrage.
        """
        executors = []
        for side in [proposal.first_side, proposal.second_side]:
            order_candidate = self.create_order_candidate(side)
            executors.append(ExecutorInfo(
                controller_id=self.config.id,
                executor_name="dca_simple",  # Example executor
                config={
                    "order_candidate": order_candidate,
                }
            ))
        return executors

    def create_order_candidate(self, side: ArbProposalSide) -> OrderCandidate:
        """
        Creates an order candidate from an arbitrage proposal side, applying slippage buffer.
        """
        slippage_buffer = self.get_slippage_buffer(side)
        price_adjustment = Decimal("1") + (slippage_buffer if side.is_buy else -slippage_buffer)
        
        # Use the price from the proposal, which already accounts for slippage from size
        price = side.order_price * price_adjustment

        return OrderCandidate(
            trading_pair=side.market_info.trading_pair,
            is_maker=False,
            trade_type=TradeType.BUY if side.is_buy else TradeType.SELL,
            order_type=OrderType.TAKER,
            amount=side.amount,
            price=price,
        )

    def get_slippage_buffer(self, side: ArbProposalSide) -> Decimal:
        if side.market_info.market.name == self.config.connector_1:
            return self.config.market_1_slippage_buffer
        return self.config.market_2_slippage_buffer

    def on_buy_order_completed(self, event: BuyOrderCompletedEvent):
        self.log_with_clock(f"Buy order completed: {event}")

    def on_sell_order_completed(self, event: SellOrderCompletedEvent):
        self.log_with_clock(f"Sell order completed: {event}")

    def get_markets_df(self) -> pd.DataFrame:
        """
        Returns a DataFrame with market information.
        """
        data = []
        for market_name, market_info in self.connectors.items():
            market = market_info.market
            trading_pair = market_info.trading_pair
            buy_price = market.get_price_by_type(trading_pair, OrderType.TAKER)
            sell_price = market.get_price_by_type(trading_pair, OrderType.MAKER)
            mid_price = (buy_price + sell_price) / 2
            data.append([
                market.display_name,
                trading_pair,
                sell_price,
                buy_price,
                mid_price,
            ])
        return pd.DataFrame(data=data, columns=["Exchange", "Market", "Sell Price", "Buy Price", "Mid Price"])

    def get_assets_df(self) -> pd.DataFrame:
        """
        Returns a DataFrame with asset information.
        """
        return self.balance_df()

    def get_active_orders_df(self) -> pd.DataFrame:
        """
        Returns a DataFrame with active orders.
        """
        data = []
        for order in self.active_orders:
            data.append([
                order.trading_pair,
                order.trade_type.name,
                order.amount,
                order.price,
            ])
        return pd.DataFrame(data=data, columns=["Market", "Side", "Amount", "Price"])

    def get_profitability_msg(self, proposal: ArbProposal) -> List[str]:
        """
        Returns a message with the profitability of the last evaluated proposal.
        """
        profit_pct = proposal.profit_pct(account_for_fee=True)
        return [f"  - Last Optimal Proposal: Size {proposal.first_side.amount:.6f}, Profitability: {profit_pct:.2%}"]
