import React, { useState, useEffect } from "react";
import ClientView from "./views/ClientView";
import AdminView from "./views/AdminView";

export default function App() {
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  if (currentPath.startsWith("/admin")) {
    return <AdminView />;
  }

  return <ClientView />;
}
