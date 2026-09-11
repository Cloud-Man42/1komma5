import { PublisherDetailView } from "@/components/modules-devices/store/PublishersView";

type Props = { params: Promise<{ publisherId: string }> };

export default async function StorePublisherPage({ params }: Props) {
  const { publisherId } = await params;
  return <PublisherDetailView publisherId={decodeURIComponent(publisherId)} />;
}
