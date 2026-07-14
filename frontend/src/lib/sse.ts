/** Parses a fetch Response body as newline-delimited Server-Sent Events
 * (`data: {...}\n\n` frames) and yields the parsed JSON payload of each. */
export async function* parseSseStream<T>(response: Response): AsyncGenerator<T> {
  if (!response.body) {
    throw new Error("Response has no body to stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        for (const line of frame.split("\n")) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;

          const payload = trimmed.slice("data:".length).trim();
          if (!payload) continue;

          try {
            yield JSON.parse(payload) as T;
          } catch {
            // Ignore malformed frames rather than aborting the whole stream.
          }
        }
      }
    }
  } finally {
    try {
      await reader.cancel();
    } catch {
      // Already closed/aborted — nothing to do.
    }
  }
}
