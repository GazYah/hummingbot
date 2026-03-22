from decimal import Decimal
from hummingbot.client.config.config_data_types import ClientFieldData
from hummingbot.strategy.v2.data_types import ConnectorPair
from hummingbot.strategy.v2.strategies.amm_arb_v2.main import AmmArbV2Config

class AmmArbV2Config(AmmArbV2Config):
    """
    Configuration for the AMM Arbitrage V2 strategy with dynamic order sizing.
    """
    connector_1: str = "binance"
    trading_pair_1: str = "BTC-USDT"
    connector_2: str = "uniswap_v2"
    trading_pair_2: str = "WBTC-WETH"

    # --- Dynamic Order Sizing Parameters ---
    min_order_amount: Decimal = ClientFieldData(
        default=Decimal("0.01"),
        prompt=lambda: "What is the minimum order amount to consider for an arbitrage trade?",
        prompt_on_new=True
    )
    max_order_amount: Decimal = ClientFieldData(
        default=Decimal("1.0"),
        prompt=lambda: "What is the maximum order amount to consider for an arbitrage trade?",
        prompt_on_new=True
    )
    min_profitability: Decimal = ClientFieldData(
        default=Decimal("0.005"),
        prompt=lambda: "What is the minimum profitability (as a decimal, e.g., 0.005 for 0.5%)?",
        prompt_on_new=True
    )

    # --- Slippage Buffers ---
    market_1_slippage_buffer: Decimal = ClientFieldData(
        default=Decimal("0.01"),
        prompt=lambda: "Enter the slippage buffer for the first market (e.g., 0.01 for 1%):",
        prompt_on_new=False
    )
    market_2_slippage_buffer: Decimal = ClientFieldData(
        default=Decimal("0.01"),
        prompt=lambda: "Enter the slippage buffer for the second market (e.g., 0.01 for 1%):",
        prompt_on_new=False
    )

    @property
    def markets(self) -> dict[str, ConnectorPair]:
        return {
            "market_1": ConnectorPair(connector=self.connector_1, trading_pair=self.trading_pair_1),
            "market_2": ConnectorPair(connector=self.connector_2, trading_pair=self.trading_pair_2),
        }
