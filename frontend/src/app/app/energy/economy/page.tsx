"use client";

import { MobileEconomyView } from "@/components/mobile/MobileEnergyViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileEconomyPage() {
  return (
    <MobileSectionPage title="Economy" subtitle="Cost and savings" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data, slugs }) => <MobileEconomyView data={data} slugs={slugs} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
