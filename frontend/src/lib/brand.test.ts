import { APP_ACRONYM, APP_DESCRIPTION, APP_NAME, APP_TITLE } from "./brand";

describe("brand", () => {
  it("uses EMIC naming", () => {
    expect(APP_ACRONYM).toBe("EMIC");
    expect(APP_NAME).toBe("Energy Monitoring In a Cloud");
    expect(APP_TITLE).toBe("EMIC — Energy Monitoring In a Cloud");
    expect(APP_DESCRIPTION).toContain("EMIC");
  });
});
