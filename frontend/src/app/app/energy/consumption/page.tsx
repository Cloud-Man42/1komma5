"use client";

import { MobileConsumptionView } from "@/components/mobile/MobileEnergyViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileConsumptionPage() {
  return (
    <MobileSectionPage title="Consumption" subtitle="Load now and today" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data }) => <MobileConsumptionView data={data} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
