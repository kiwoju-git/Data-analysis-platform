import { ChartTooltip } from "./ChartTooltip";
import { t } from "../i18n/translate";
import type { useChartItemInteraction } from "./useChartItemInteraction";

export interface ChartDetailItem {
  id: string;
  title: string;
  details: ReadonlyArray<{ label: string; value: string }>;
}

export function ChartItemFeedback({ interaction, items, collapsible = false }: {
  interaction: ReturnType<typeof useChartItemInteraction>;
  items: readonly ChartDetailItem[];
  collapsible?: boolean;
}) {
  const active = items.find((item) => item.id === interaction.activeItem?.id);
  const selected = items.find((item) => item.id === interaction.detailId);
  return <>
    {active && interaction.activeItem?.anchor && <ChartTooltip
      id={interaction.tooltipId} title={active.title} details={active.details}
      anchor={interaction.activeItem.anchor} />}
    {collapsible ? <details className="chart-selected-detail" open>
      <summary>{t("charts.selectedDetails")}</summary>
      <p aria-live="polite" aria-atomic="true">{selected && <><strong>{selected.title}</strong>{": "}
        {selected.details.map((detail) => `${detail.label} ${detail.value}`).join("; ")}</>}</p>
    </details> : <p className="chart-selected-detail" aria-live="polite" aria-atomic="true">
      {selected && <><strong>{selected.title}</strong>{": "}
        {selected.details.map((detail) => `${detail.label} ${detail.value}`).join("; ")}</>}
    </p>}
  </>;
}
