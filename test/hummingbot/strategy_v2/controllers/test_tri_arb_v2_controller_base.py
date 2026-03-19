import asyncio
from decimal import Decimal
from test.isolated_asyncio_wrapper_test_case import IsolatedAsyncioWrapperTestCase
from unittest.mock import AsyncMock, MagicMock

from hummingbot.data_feed.market_data_provider import MarketDataProvider
from hummingbot.strategy_v2.controllers.tri_arb_v2.tri_arb_v2_config import (
    TriArbV2ControllerBase,
    TriArbV2ControllerConfigBase,
)
from hummingbot.strategy_v2.executors.data_types import ConnectorPair


class TestTriArbV2ControllerConfigBase(IsolatedAsyncioWrapperTestCase):
    def setUp(self):
        super().setUp()
        # Mocking dependencies
        self.mock_market_data_provider = MagicMock(spec=MarketDataProvider)
        self.mock_actions_queue = AsyncMock(spec=asyncio.Queue)

    def test_config_creation_and_validation(self):
        """
        Tests that the config can be created and that its validators work as expected.
        """
        config = TriArbV2ControllerConfigBase(
            binance_connector="binance",
            binance_pairs="BTC-USDT, ETH-USDT",
            uniswap_connector="uniswap",
            uniswap_pair="WETH-USDC",
            min_profitability=Decimal("0.01"),
            max_dollar_hardcap_trade_amount=Decimal("50"),
        )
        self.assertEqual(config.binance_connector, "binance")
        self.assertEqual(config.binance_pairs, ["BTC-USDT", "ETH-USDT"])
        self.assertEqual(config.uniswap_connector, "uniswap")
        self.assertEqual(config.uniswap_pair, "WETH-USDC")

    def test_controller_instantiation_and_initialization(self):
        """
        Tests that the controller can be instantiated and that it initializes the rate sources correctly.
        """
        config = TriArbV2ControllerConfigBase(
            binance_connector="binance",
            binance_pairs="BTC-USDT, ETH-USDT",
            uniswap_connector="uniswap",
            uniswap_pair="WETH-USDC",
        )

        # Instantiate the controller
        controller = TriArbV2ControllerBase(
            config=config,
            market_data_provider=self.mock_market_data_provider,
            actions_queue=self.mock_actions_queue
        )

        # Check if the controller has been initialized correctly
        self.assertEqual(controller.config, config)

        # Check if initialize_rate_sources was called with the correct arguments
        self.mock_market_data_provider.initialize_rate_sources.assert_called_once_with([
            ConnectorPair(connector_name="binance", trading_pair="BTC-USDT"),
            ConnectorPair(connector_name="binance", trading_pair="ETH-USDT"),
            ConnectorPair(connector_name="uniswap", trading_pair="WETH-USDC"),
        ])
