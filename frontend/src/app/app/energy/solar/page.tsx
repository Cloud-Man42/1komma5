"use client";

import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSolarView } from "@/components/mobile/MobileEnergyViews";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileSolarPage() {
  return (
    <MobileSectionPage title="Solar" subtitle="Production and forecast" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data, slugs }) => <MobileSolarView data={data} slugs={slugs} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
