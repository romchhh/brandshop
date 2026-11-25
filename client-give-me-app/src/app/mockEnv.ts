import { mockTelegramEnv, parseInitData, retrieveLaunchParams } from "@telegram-apps/sdk-react";

/**
 * Лише в браузері. Поза Telegram — mock, щоб SDK не падав на звичайному сайті.
 */
function setupWebTelegramMock(): void {
  if (typeof window === "undefined") {
    return;
  }

  let shouldMock = false;
  try {
    retrieveLaunchParams();
    shouldMock = !!sessionStorage.getItem("____mocked");
  } catch {
    shouldMock = true;
  }

  if (!shouldMock) {
    return;
  }

  const initDataRaw = new URLSearchParams([
    [
      "user",
      JSON.stringify({
        id: 1,
        first_name: "Web",
        last_name: "Guest",
        username: "web_guest",
        language_code: "uk",
        is_premium: false,
        allows_write_to_pm: false,
      }),
    ],
    ["hash", "web_guest_mock_hash"],
    ["auth_date", String(Math.floor(Date.now() / 1000))],
    ["start_param", "web"],
    ["chat_type", "sender"],
    ["chat_instance", "1"],
  ]).toString();

  mockTelegramEnv({
    themeParams: {
      accentTextColor: "#007AFF",
      bgColor: "#ffffff",
      buttonColor: "#007AFF",
      buttonTextColor: "#ffffff",
      destructiveTextColor: "#ec3942",
      headerBgColor: "#ffffff",
      hintColor: "#8e8e93",
      linkColor: "#007AFF",
      secondaryBgColor: "#f2f2f7",
      sectionBgColor: "#ffffff",
      sectionHeaderTextColor: "#007AFF",
      subtitleTextColor: "#8e8e93",
      textColor: "#111111",
    },
    initData: parseInitData(initDataRaw),
    initDataRaw,
    version: "7.2",
    platform: "web",
  });
  try {
    sessionStorage.setItem("____mocked", "1");
  } catch {
    /* private mode */
  }
}

setupWebTelegramMock();
