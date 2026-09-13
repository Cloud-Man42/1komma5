"use client";

import { MobileForecastView } from "@/components/mobile/MobileEnergyViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileForecastPage() {
  return (
    <MobileSectionPage title="Forecast" subtitle="Solar production forecast" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data, slugs }) => <MobileForecastView slugs={slugs} data={data} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
