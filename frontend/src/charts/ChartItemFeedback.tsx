import { ChartTooltip } from "./ChartTooltip";
import type { useChartItemInteraction } from "./useChartItemInteraction";

export interface ChartDetailItem {
  id: string;
  title: string;
  details: ReadonlyArray<{ label: string; value: string }>;
}

export function ChartItemFeedback({ interaction, items }: {
  interaction: ReturnType<typeof useChartItemInteraction>;
  items: readonly ChartDetailItem[];
}) {
  const active = items.find((item) => item.id === interaction.activeItem?.id);
  const selected = items.find((item) => item.id === interaction.detailId);
  return <>
    {active && interaction.activeItem?.anchor && <ChartTooltip
      id={interaction.tooltipId} title={active.title} details={active.details}
      anchor={interaction.activeItem.anchor} />}
    <p className="chart-selected-detail" aria-live="polite" aria-atomic="true">
      {selected && <><strong>{selected.title}</strong>{": "}
        {selected.details.map((detail) => `${detail.label} ${detail.value}`).join("; ")}</>}
    </p>
  </>;
}
