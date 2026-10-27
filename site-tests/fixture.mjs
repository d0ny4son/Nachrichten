// Beispieldaten nach Schema v1 für die App-Tests.
export const NOW = new Date("2026-10-27T11:00:00Z");

const item = (id, source, title, keywords, extra = {}) => ({
  id, source, title, link: `https://example.org/${id}`,
  published: "2026-10-27T10:00:00Z", image: null, plus: false, keywords, ...extra,
});

export const DATA = {
  version: 1,
  generated_at: "2026-10-27T10:55:00Z",
  sources: {
    tagesschau: { name: "Tagesschau", media_type: "oeffentlich-rechtlich" },
    zeit: { name: "Zeit", media_type: "zeitung" },
    dw: { name: "Deutsche Welle", media_type: "international" },
  },
  stories: [
    { id: "s1", score: 3, region: "inland", categories: ["wirtschaft"], latest: "2026-10-27T10:00:00Z", lead: "a1",
      items: [item("a1", "tagesschau", "Bundestag debattiert Haushalt", ["bundestag", "haushalt"]),
              item("a2", "zeit", "Haushaltsdebatte im Bundestag", ["haushaltsdebatte", "bundestag"])] },
    { id: "s2", score: 2, region: "ausland", categories: [], latest: "2026-10-27T09:00:00Z", lead: "b1",
      items: [item("b1", "dw", "Neues Wasserstoffnetz in Europa", ["wasserstoffnetz", "europa"])] },
    { id: "s3", score: 1, region: null, categories: ["sport", "wissenschaft"], latest: "2026-10-27T10:30:00Z", lead: "c1",
      items: [item("c1", "zeit", "Ärztekammer warnt vor Hitze beim Fußball", ["ärztekammer", "hitze", "fußball"])] },
  ],
};
