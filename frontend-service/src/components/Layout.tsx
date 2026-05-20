import type { PropsWithChildren } from "react";

import { Header } from "./Header";


export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="app-layout">
      <Header />
      <main className="app-shell app-main">{children}</main>
    </div>
  );
}
