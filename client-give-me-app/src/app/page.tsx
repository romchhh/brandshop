"use client";

import Home from "@/components/Home";
import {useMount} from "react-use";

export default function Page() {
  useMount(() => {
    window.Telegram?.WebApp?.expand()
  })

  return <Home />;
}
