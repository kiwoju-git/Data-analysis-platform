import { useChartItemInteraction } from "./useChartItemInteraction";

export function useChartPointInteraction(itemIds: string[] = []) {
  const interaction = useChartItemInteraction(itemIds);
  return { ...interaction, activePoint: interaction.activeItem };
}
