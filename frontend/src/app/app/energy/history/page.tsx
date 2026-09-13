"use client";

import { MobileHistoryView } from "@/components/mobile/MobileEnergyViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileHistoryPage() {
  return (
    <MobileSectionPage title="History" subtitle="Energy history by site" backHref="/app/energy">
      <MobileSummaryLoader>
        {({ data }) => <MobileHistoryView data={data} />}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
