import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  readRunningGame: vi.fn(),
  setCurrentGame: vi.fn(),
}));

vi.mock("./runningGame", () => ({
  readRunningGame: mocks.readRunningGame,
}));

vi.mock("../api", () => ({
  setCurrentGame: mocks.setCurrentGame,
}));

import { startGameWatcher } from "./gameWatcher";

const steamGlobal = globalThis as any;

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

describe("startGameWatcher", () => {
  let notify: (() => void) | null = null;

  beforeEach(() => {
    notify = null;
    mocks.readRunningGame.mockReset();
    mocks.setCurrentGame.mockReset();
    mocks.setCurrentGame.mockResolvedValue({});
    steamGlobal.SteamClient = {
      GameSessions: {
        RegisterForAppLifetimeNotifications: (cb: () => void) => {
          notify = cb;
          return { unregister: vi.fn() };
        },
      },
    };
  });

  afterEach(() => {
    delete steamGlobal.SteamClient;
  });

  it("reports null after a game exits", async () => {
    mocks.readRunningGame.mockReturnValue({ appid: "42", name: "Game" });
    const stop = startGameWatcher();
    await flushPromises();

    mocks.readRunningGame.mockReturnValue(null);
    notify?.();
    await flushPromises();
    stop();

    expect(mocks.setCurrentGame).toHaveBeenCalledTimes(2);
    expect(mocks.setCurrentGame).toHaveBeenNthCalledWith(1, "42");
    expect(mocks.setCurrentGame).toHaveBeenNthCalledWith(2, null);
  });
});
