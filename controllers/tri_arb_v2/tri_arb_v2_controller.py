import asyncio
from decimal import Decimal
from typing import List

from pydantic import Field, field_validator

from hummingbot.core.data_type.common import MarketDict
from hummingbot.strategy_v2.controllers.controller_base import ControllerBase, ControllerConfigBase
from hummingbot.strategy_v2.executors.data_types import ConnectorPair


class TriArbV2ControllerConfig(ControllerConfigBase):
    """
    Placeholder text for TriArbV2ControllerConfig.
    """
    controller_name: str = "tri_arb_v2_controller"
    controller_type: str = "tri_arb_v2"

    binance_connector: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter the connector name for Binance (e.g., binance_perpetual): ",
            "prompt_on_new": True,
            "is_updatable": False
        }

    )

    # Note: typehints are used by pytest to validate input type,
    # however the actual input is a comma-separated string that is parsed in the validator into a list of strings.
    binance_pairs: List[str] = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter the Binance trading pairs (comma separated, e.g., BTC-USDT,ETH-USDT): ",
            "prompt_on_new": True,
            "is_updatable": False
        }
    )

    uniswap_connector: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter the connector name for Uniswap (e.g., uniswap): ",
            "prompt_on_new": True,
            "is_updatable": False
        }
    )

    uniswap_pair: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter the Uniswap trading pair (e.g., WETH-USDC): ",
            "prompt_on_new": True,
            "is_updatable": False
        }
    )

    min_profitability: Decimal = Field(
        default=Decimal("0.01"),
        json_schema_extra={
            "prompt": "Enter the minimum profitability threshold (e.g., 0.01 for 1%): ",
            "prompt_on_new": True,
            "is_updatable": True
        }
    )

    max_dollar_hardcap_trade_amount: Decimal = Field(
        default=Decimal("50"),
        json_schema_extra={
            "prompt": "Enter the maximum hardcap trade amount in dollars (e.g., 50): ",
            "prompt_on_new": True,
            "is_updatable": True
        }
    )

    @field_validator('binance_pairs', mode="before")
    @classmethod
    def validate_binance_pairs(cls, v):
        if isinstance(v, list):
            pairs = [pair.strip().upper() for pair in v]
        elif isinstance(v, str):
            pairs = [pair.strip().upper() for pair in v.split(',')]
        else:
            raise TypeError("Binance trading pairs must be provided as a comma-separated string or list.")

        if len(pairs) != 2:
            raise ValueError("Exactly two Binance trading pairs must be provided, separated by a comma.")
        else:
            return pairs

    @field_validator('uniswap_pair', mode="before")
    @classmethod
    def validate_uniswap_pair(cls, v):
        if not isinstance(v, str):
            raise TypeError("Uniswap trading pair must be provided as a string.")
        pair = v.strip().upper()
        if '-' not in pair:
            raise ValueError("Uniswap trading pair must be in the format 'TOKEN1-TOKEN2' (e.g., WETH-USDC).")
        return pair

    @field_validator('min_profitability', mode="before")
    @classmethod
    def validate_min_profitability(cls, v):
        if not isinstance(v, (str)):
            raise TypeError("Minimum profitability threshold must be a number (e.g., 0.01 for 1%).")
        try:
            profitability = Decimal(v)
        except Exception:
            raise ValueError("Minimum profitability threshold must be a valid decimal number.")
        if profitability < 0:
            raise ValueError("Minimum profitability threshold must be a non-negative number.")
        return profitability

    @field_validator('max_dollar_hardcap_trade_amount', mode="before")
    @classmethod
    def validate_max_dollar_hardcap_trade_amount(cls, v):
        # Allow None or empty input to represent "no cap"
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        # Accept numbers or numeric strings
        if not isinstance(v, (float, int, Decimal, str)):
            raise TypeError("Maximum dollar hardcap trade amount must be a number (e.g., 50) or empty for no cap.")
        try:
            hardcap = Decimal(str(v))
        except Exception:
            raise ValueError("Maximum dollar hardcap trade amount must be a valid decimal number.")
        if hardcap <= 0:
            raise ValueError("Maximum dollar hardcap trade amount must be a positive number.")
        return hardcap

    def update_markets(self, markets: MarketDict) -> MarketDict:
        # Only ensure both Binance pairs are present in the markets map; do not add the Uniswap pair.
        updated_markets = dict(markets) if markets is not None else {}
        binance_markets = updated_markets.setdefault(self.binance_connector, {})
        for pair in self.binance_pairs:
            binance_markets.setdefault(pair, {})
        return updated_markets


class TriArbV2Controller(ControllerBase):
    """
    Base class for TriArbV2Controller. Contains shared logic and utilities for the TriArbV2 strategy.
    """

    def __init__(self, config: TriArbV2ControllerConfig, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.config = config
        self.market_data_provider.initialize_rate_sources([
            ConnectorPair(
                connector_name=self.config.binance_connector,
                trading_pair=self.config.binance_pairs[0]),
            ConnectorPair(
                connector_name=self.config.binance_connector,
                trading_pair=self.config.binance_pairs[1]),
            ConnectorPair(
                connector_name=self.config.uniswap_connector,
                trading_pair=self.config.uniswap_pair
            )
        ]
        )

    def determine_executor_actions(self):
        return super().determine_executor_actions()

    async def update_processed_data(self):
        """
        Concurrently fetch and process market data, ready for decision making.
        """
        prices = await asyncio.gather(
            self.get_orderbook_binance(self.config.binance_pairs[0]),
            self.get_orderbook_binance(self.config.binance_pairs[1]),
        )
        print(prices)

    async def get_orderbook_binance(self, trading_pair: str):
        return self.market_data_provider.get_order_book_snapshot(self.config.binance_connector, trading_pair)

    def to_format_status(self):
        return super().to_format_status()
