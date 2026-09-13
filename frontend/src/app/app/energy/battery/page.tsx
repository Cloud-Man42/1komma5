"use client";

import { MobileBatteryView } from "@/components/mobile/MobileEnergyViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileBatteryPage() {
  return (
    <MobileSectionPage title="Battery" subtitle="Storage and charge state" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data }) => <MobileBatteryView data={data} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
