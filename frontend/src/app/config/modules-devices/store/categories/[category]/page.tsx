import { CategoryBrowseView } from "@/components/modules-devices/store/CategoryBrowseView";

type Props = { params: Promise<{ category: string }> };

export default async function StoreCategoryPage({ params }: Props) {
  const { category } = await params;
  return <CategoryBrowseView category={decodeURIComponent(category)} />;
}
