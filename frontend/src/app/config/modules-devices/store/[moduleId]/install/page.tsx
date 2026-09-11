import { InstallWizard } from "@/components/modules-devices/store/InstallWizard";

type Props = { params: Promise<{ moduleId: string }> };

export default async function StoreInstallPage({ params }: Props) {
  const { moduleId } = await params;
  return <InstallWizard moduleId={decodeURIComponent(moduleId)} />;
}
