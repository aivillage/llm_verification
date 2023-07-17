CTFd._internal.challenge.data = undefined;

CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function() {};

CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function() {};

window.Alpine = Alpine;

Alpine.data("llm_verification", () => ({
  prompt: "",
  generated_text: "",
  gen_id: "",

  async init() {
  },

  async generateText() {
    this.generated_text = "Generating...";
    url = CTFd.config.urlRoot + `/generate`;

    const response = await CTFd.fetch(url, {
      method: "POST",
      body: JSON.stringify({
        challenge_id: this.id,
        prompt: this.prompt
      }),
    });
    const result = await response.json();
    this.generated_text = result.data.text;
    this.submission = result.data.id.toString();
  },
}));