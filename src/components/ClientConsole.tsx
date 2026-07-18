"use client";

import dynamic from "next/dynamic";
import FirstVisitThanksModal from "./FirstVisitThanksModal";

const OperationsConsole = dynamic(() => import("./OperationsConsole"), {
  ssr: false,
  loading: () => <main className="boot">Cargando mapa de respuesta...</main>,
});

export default function ClientConsole() {
  return (
    <>
      <OperationsConsole />
      <FirstVisitThanksModal />
    </>
  );
}
