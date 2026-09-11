import { ModuleDetailView } from "@/components/modules-devices/store/ModuleDetailView";

type Props = { params: Promise<{ moduleId: string }> };

export default async function StoreModuleDetailPage({ params }: Props) {
  const { moduleId } = await params;
  return <ModuleDetailView moduleId={decodeURIComponent(moduleId)} />;
}
