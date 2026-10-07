import { useChartItemInteraction, type ChartInteractionOptions } from "./useChartItemInteraction";

export function useChartPointInteraction(itemIds: readonly string[] = [], options: ChartInteractionOptions = {}) {
  const interaction = useChartItemInteraction(itemIds, options);
  return { ...interaction, activePoint: interaction.activeItem };
}
