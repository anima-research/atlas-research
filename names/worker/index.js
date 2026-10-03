// Serve the site from the assets directory, with the /research/names prefix removed when
// the request comes in under atlas.lari-island.ai/research/names/.
const PREFIX = "/research/names";
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let path = url.pathname;
    if (path === PREFIX) return Response.redirect(url.origin + PREFIX + "/", 301);
    if (path.startsWith(PREFIX + "/")) path = path.slice(PREFIX.length);
    if (path === "/") path = "/index.html";
    url.pathname = path;
    return env.ASSETS.fetch(new Request(url.toString(), request));
  }
};
