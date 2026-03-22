from decimal import Decimal

from hummingbot.client.ui.interface_utils import format_df_for_printing
from hummingbot.strategy.amm_arb.amm_arb_config import AmmArbV2Config
from hummingbot.strategy.amm_arb.amm_arb_controller import AmmArbV2Controller
from hummingbot.strategy.v2.controllers_factory import ControllersFactory
from hummingbot.strategy.v2.strategy_v2_base import StrategyV2Base


class AmmArbV2(StrategyV2Base):
    """
    This is a V2 implementation of the AMM arbitrage strategy.
    It uses a controller to manage the arbitrage logic and a config class to define the parameters.
    """

    def __init__(self, config: AmmArbV2Config, controllers_factory: ControllersFactory):
        super().__init__(config, controllers_factory)
        self.config = config

    def format_status(self) -> str:
        if not self.is_ready():
            return "Strategy not ready yet."

        controller: AmmArbV2Controller = self.controllers["main"]
        markets_df = controller.get_markets_df()
        assets_df = controller.get_assets_df()

        lines = ["\n# Markets"]
        lines.extend(["", "  " + line for line in format_df_for_printing(markets_df).split("\n")])

        lines.extend(["\n# Assets"])
        lines.extend(["", "  " + line for line in format_df_for_printing(assets_df).split("\n")])

        lines.extend(["\n# Active Orders"])
        if len(controller.active_orders) > 0:
            active_orders_df = controller.get_active_orders_df()
            lines.extend(["", "  " + line for line in format_df_for_printing(active_orders_df).split("\n")])
        else:
            lines.append("  No active orders.")

        lines.extend(["\n# Profitability"])
        if controller.last_proposal:
            profitability_msg = controller.get_profitability_msg(controller.last_proposal)
            lines.extend(["", "  " + line for line in profitability_msg])
        else:
            lines.append("  No arbitrage opportunities found yet.")

        return "\n".join(lines)
