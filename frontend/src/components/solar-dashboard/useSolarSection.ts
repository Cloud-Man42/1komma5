"use client";



import { useEffect, useState } from "react";

import { readSolarSectionFromLocation, type SolarSectionId } from "./solarSection";



export function useSolarSection(): { section: SolarSectionId } {

  const [section, setSection] = useState<SolarSectionId>(() => readSolarSectionFromLocation());



  useEffect(() => {

    const update = () => setSection(readSolarSectionFromLocation());

    update();

    window.addEventListener("hashchange", update);

    window.addEventListener("popstate", update);

    return () => {

      window.removeEventListener("hashchange", update);

      window.removeEventListener("popstate", update);

    };

  }, []);



  return { section };

}


