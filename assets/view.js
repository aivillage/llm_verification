if (CTFd._internal.challenge) {
  var challenge = CTFd._internal.challenge;
} else {
  var challenge = window.challenge;
}

if (CTFd.lib.$) {
  $ = CTFd.lib.$;
}

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


async function generate_text(challenge_id, prompt) {
  var domain = CTFd.config.urlRoot;
  var path = "generate";
  var body = {
    challenge_id: challenge_id,
    prompt: prompt
  };

  var headers = {};
  headers["Accept"] = ["application/json"];
  headers["Content-Type"] = ["application/json"];
  headers["X-CSRFToken"] = [CTFd.config.csrfNonce];
  var response = fetch(domain + path, {
    method: "POST",
    headers,
    body: JSON.stringify(body)
  })
    .then((response) => {
      return response.json();
    });
  return response;
};

function htmlEntities(string) {
  return $("<div/>")
    .text(string)
    .html();
}

challenge.data = undefined;

challenge.renderer = CTFd.lib.markdown();

challenge.preRender = function() {};

challenge.render = function(markdown) {
  return challenge.renderer.render(markdown);
};

challenge.postRender = function() {
  // Don't hijack the enter button
  // Clone element to remove keyup event handler. Not sure why .off wont work
  $("#challenge-input").replaceWith($("#challenge-input").clone());

  var submission_template =
    '<div class="card bg-light mb-4">\
    <div class="card-body">\
        <blockquote class="blockquote mb-0">\
            <p>{0}</p>\
            <p>{1}</p>\
            <small class="text-muted">submitted {2}</small>\
            <br>\
            <small class="text-muted">graded {3}</small>\
        </blockquote>\
    </div>\
  </div>';

  // Define a template for pending submissions that doesn't include "graded."
  var pending_submission_template =
    '<div class="card bg-light mb-4">\
    <div class="card-body">\
        <blockquote class="blockquote mb-0">\
            <p>{0}</p>\
            <p>{1}</p>\
            <small class="text-muted">submitted {2}</small>\
        </blockquote>\
    </div>\
  </div>';

  // Populate Submissions
  var challenge_id = parseInt($("#challenge-id").val());
  var url = "/submissions/" + challenge_id;

  CTFd.fetch(url, {
    method: "GET",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    }
  })
    .then(function(response) {
      return response.json();
    })
    .then(function(response) {
      var correct = response["data"]["correct"];
      var pending = response["data"]["pending"];
      var awarded = response["data"]["awarded"];
      var incorrect = response["data"]["incorrect"];

      $("#challenge-submissions").empty();
      $("#challenge-submissions").append($("<br>"));
      $("#challenge-submissions").append($("<h3>Correct</h3>"));
      for (var index = 0; index < correct.length; index++) {
        var submission = correct[index];
        var entry = $(
          submission_template.format(
            htmlEntities(submission.prompt),
            htmlEntities(submission.generated_text),
            Moment(submission.date).fromNow()
          )
        );
        $("#challenge-submissions").append(entry);
      }

      $("#challenge-submissions").append($("<br>"));
      $("#challenge-submissions").append($("<hr>"));
      $("#challenge-submissions").append($("<br>"));

      $("#challenge-submissions").append($("<h3>Awarded</h3>"));
      for (var index = 0; index < awarded.length; index++) {
        var submission = awarded[index];
        var entry = $(
          submission_template.format(
            htmlEntities(submission.prompt),
            htmlEntities(submission.generated_text),
            Moment(submission.date).fromNow()
          )
        );
        $("#challenge-submissions").append(entry);
      }

      $("#challenge-submissions").append($("<br>"));
      $("#challenge-submissions").append($("<hr>"));
      $("#challenge-submissions").append($("<br>"));

      $("#challenge-submissions").append($("<h3>Pending</h3>"));
      for (var index = 0; index < pending.length; index++) {
        var submission = pending[index];
        var entry = $(
          pending_submission_template.format(
            htmlEntities(submission.prompt),
            htmlEntities(submission.generated_text),
            Moment(submission.date).fromNow(),
          )
        );
        $("#challenge-submissions").append(entry);
      }

      $("#challenge-submissions").append($("<br>"));
      $("#challenge-submissions").append($("<hr>"));
      $("#challenge-submissions").append($("<br>"));

      $("#challenge-submissions").append($("<h3>Incorrect</h3>"));
      for (var index = 0; index < incorrect.length; index++) {
        var submission = incorrect[index];
        var entry = $(
          submission_template.format(
            htmlEntities(submission.prompt),
            htmlEntities(submission.generated_text),
            Moment(submission.date).fromNow()
          )
        );
        $("#challenge-submissions").append(entry);
      }

      // Fix prompt text and generate button
      $("#challenge-window #challenge-generate").addClass(
        "btn btn-md btn-outline-secondary float-right"
      );
      $("#challenge-window #challenge-generate-loading").addClass(
        "btn btn-md btn-outline-secondary float-right"
      );
      $("#challenge-window #challenge-prompt").addClass("form-control");

      $("#challenge-generate").click(function(event) {
        event.preventDefault();
  
        $("#challenge-input").val();
        
        var challenge_id = $("#challenge-id").val();
        var prompt = $("#challenge-prompt").val();
        generate_text(challenge_id, prompt).then(function(response) {
          challenge.gen_id = response.data.id;
          $("#challenge-input").val(response.data.text);
        });
      });
    });
};

challenge.submit = function(preview) {
  var challenge_id = parseInt($("#challenge-id").val());
  
  var body = {
    challenge_id: challenge_id,
    submission: challenge.gen_id.toString(),
  };
  var params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
    if (response.status === 429) {
      // User was ratelimited but process response
      return response;
    }
    if (response.status === 403) {
      // User is not logged in or CTF is paused.
      return response;
    }
    return response;
  });
};
