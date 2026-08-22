import React from "react";
import { vi } from "vitest";

export function mockNextNavigation(params: Record<string, string> = { slug: "akarp" }) {
  vi.mock("next/navigation", () => ({
    useParams: () => params,
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      refresh: vi.fn(),
    }),
    usePathname: () => "/",
    useSearchParams: () => new URLSearchParams(),
  }));
}

export function mockNextLink() {
  vi.mock("next/link", () => ({
    default: ({
      href,
      children,
      ...rest
    }: {
      href: string;
      children: React.ReactNode;
    }) => (
      <a href={href} {...rest}>
        {children}
      </a>
    ),
  }));
}

export function mockNextImage() {
  vi.mock("next/image", () => ({
    default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => {
      return <img alt="" {...props} />;
    },
  }));
}
