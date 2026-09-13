"use client";

import { MobileGridView } from "@/components/mobile/MobileEnergyViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileGridPage() {
  return (
    <MobileSectionPage title="Grid" subtitle="Import, export and net" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data }) => <MobileGridView data={data} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
