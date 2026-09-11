export function packageErrorLabel(code: string | undefined): string {
  switch (code) {
    case "INVALID_MANIFEST":
      return "Ogiltig manifestfil.";
    case "SIGNATURE_INVALID":
      return "Ogiltig signatur. Paketet kan inte installeras.";
    case "PUBLISHER_UNKNOWN":
      return "Publisher är inte betrodd.";
    case "PUBLISHER_REVOKED":
      return "Publisher-nyckeln är återkallad.";
    case "PACKAGE_TOO_LARGE":
      return "Paketet är för stort.";
    case "MODULE_ALREADY_INSTALLED":
      return "Modulen är redan installerad.";
    case "MISSING_DEPENDENCY":
      return "Saknar obligatoriskt modulberoende.";
    case "DEPENDENCY_CYCLE":
      return "Modulberoenden bildar en cykel.";
    case "VERSION_DOWNGRADE_NOT_ALLOWED":
      return "Nedgradering är inte tillåten utan explicit adminåtgärd.";
    case "MODULE_IN_USE":
      return "Modulen används och kan inte tas bort.";
    case "MODULE_HAS_DEVICES":
      return "Modulen har registrerade enheter och kan inte tas bort.";
    case "PACKAGE_QUARANTINED":
      return "Paketet är i karantän.";
    case "HEALTH_GATE_FAILED":
      return "Hälsokontroll misslyckades efter uppdatering.";
    case "VERSION_MISMATCH":
      return "Installerad och runtime-version matchar inte.";
    case "INVALID_PERMISSION":
      return "Paketet begär ogiltiga permissions.";
    case "PERMISSION_CAPABILITY_MISMATCH":
      return "Capabilities matchar inte de deklarerade permissions.";
    case "MODULE_ID_PROTECTED":
      return "Modul-ID är skyddat.";
    case "PACKAGE_LOCKED":
      return "Paketoperation pågår redan.";
    default:
      return code ?? "Okänt paketfel";
  }
}

export function packageStateLabel(state: string): string {
  switch (state) {
    case "installed":
      return "Installerad";
    case "quarantined":
      return "Karantän";
    case "broken":
      return "Trasig";
    case "removing":
      return "Tar bort";
    case "update_available":
      return "Uppdatering tillgänglig";
    default:
      return state;
  }
}

export function trustBadgeLabel(key: "signed" | "signature_valid" | "publisher_trusted" | "install_allowed", value: boolean): string {
  const labels = {
    signed: value ? "Signerad" : "Osignerad",
    signature_valid: value ? "Signatur giltig" : "Signatur ogiltig",
    publisher_trusted: value ? "Publisher betrodd" : "Publisher ej betrodd",
    install_allowed: value ? "Installation tillåten" : "Installation blockerad",
  };
  return labels[key];
}
