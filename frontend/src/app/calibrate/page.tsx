import { EnergySceneCalibrator } from "@/components/EnergySceneCalibrator";

export default async function CalibratePage({
  searchParams,
}: {
  searchParams?: Promise<{ site?: string }>;
}) {
  const params = (await searchParams) ?? {};
  const siteSlug = params.site ?? "default";

  return (
    <section className="calibrator-page">
      <header className="calibrator-page-header">
        <h1>Kalibrera energikablar</h1>
        <p>
          Anpassa bakgrundsbild, utrustning och kabelvägar. Växla mellan visningsläge och
          redigeringsläge. Ändringar sparas automatiskt och gäller samma scen på dashboard och alla
          site-sidor.
        </p>
      </header>
      <EnergySceneCalibrator siteSlug={siteSlug} />
    </section>
  );
}
