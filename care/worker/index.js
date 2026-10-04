// Serve the site from the assets directory, with the /research/care prefix removed when
// the request comes in under atlas.lari-island.ai/research/care/.
const PREFIX = "/research/care";
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
