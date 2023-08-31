CTFd._internal.challenge.data = undefined;

CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function() {};

CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function() {};

window.Alpine = Alpine;

function Moment(d) {
  var date = new Date(d);
  date.fromNow = function() {
      var delta = Math.round((+new Date() - this) / 1000);

      var minute = 60,
      hour = minute * 60,
      day = hour * 24,
      week = day * 7;

      var fuzzy;

      if (delta < 30) {
          fuzzy = "just now";
      } else if (delta < minute) {
          fuzzy = delta + " seconds ago.";
      } else if (delta < 2 * minute) {
          fuzzy = "a minute ago";
      } else if (delta < hour) {
          fuzzy = Math.floor(delta / minute) + " minutes ago";
      } else if (Math.floor(delta / hour) == 1) {
          fuzzy = "1 hour ago";
      } else if (delta < day) {
          fuzzy = Math.floor(delta / hour) + " hours ago";
      } else if (delta < day * 2) {
          fuzzy = "yesterday";
      } else if (delta < day * 3) {
          fuzzy = "two days ago";
      } else if (delta < day * 4) {
          fuzzy = "three days ago";
      } else {
          fuzzy = "more than three days ago";
      }
      return fuzzy;
  };
  return date;
}

Alpine.data("llm_verification", () => ({
  prompt: "",
  generated_text: "",
  history: [],
  chat_limit: 0,
  is_single_turn: true,
  is_multi_turn: false,
  gen_id: -1,
  show_generate: true,
  show_submissions: false,
  submissions: [],
  models_left: [],
  show_submit: true,
  show_done: false,

  async init() {
    url = CTFd.config.urlRoot + `/chat_limit/` + this.id;

    const response = await CTFd.fetch(url, {
      method: "get",
    });
    const result = await response.json();
    this.chat_limit = result.data.chat_limit;
    if (this.chat_limit != 0) {
      this.is_single_turn = false;
      this.is_multi_turn = true;
    }
    await this.getModelsLeft();
  },

  async generateText() {
    if (this.prompt == "") {
      alert("Please enter a prompt!");
      return;
    }
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
    this.history = result.data.history;
    if (result.data.history != []) {
      this.prompt = "";
    }
    this.gen_id = result.data.gen_id;
    this.submission = result.data.id.toString();
  },

  async showGenerate() {
    this.show_generate = true;
    this.show_submissions = false;
  },

  async showSubmissions() {
    await this.getSubmissions();
    this.show_generate = false;
    this.show_submissions = true;
  },

  async getSubmissions() {
    url = CTFd.config.urlRoot + `/submissions/` + this.id;

    const response = await CTFd.fetch(url, {
      method: "get",
    });
    const result = await response.json();
    this.submissions = result.data.submissions;
    this.models_left = result.data.models_left;
    for (var i = 0; i < this.submissions.length; i++) {
      this.submissions[i].date = Moment(this.submissions[i].date).fromNow();
    }
    if (this.models_left.length == 0) {
      this.show_submit = false;
      this.show_done = true;
    }
  },

  async getModelsLeft() {
    url = CTFd.config.urlRoot + `/models_left/` + this.id;

    const response = await CTFd.fetch(url, {
      method: "get",
    });
    const result = await response.json();
    this.models_left = result.data.models_left;
    if (this.models_left.length == 0) {
      this.show_submit = false;
      this.show_done = true;
    }
  },

  async submitGenerated() {
    if (this.gen_id == "") {
      alert("Please generate a text first!");
      return;
    }
    await this.submitChallenge();
    await this.getModelsLeft();
  }
}));
