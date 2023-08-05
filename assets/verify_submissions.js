if (CTFd.lib.$) {
  $ = CTFd.lib.$;
}

function htmlentities(string) {
  return $("<div/>")
    .text(string)
    .html();
}

function ezgrade(args) {
  var modal =
    '<div class="modal fade" tabindex="-1" role="dialog">' +
    '  <div class="modal-dialog" role="document">' +
    '    <div class="modal-content">' +
    '      <div class="modal-header">' +
    '        <h5 class="modal-title">{0}</h5>' +
    '        <button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
    '          <span aria-hidden="true">&times;</span>' +
    "        </button>" +
    "      </div>" +
    '      <div class="modal-body">' +
    "        <p>{1}</p>" +
    "      </div>" +
    '      <div class="modal-footer">' +
    "      </div>" +
    "    </div>" +
    "  </div>" +
    "</div>";
  var res = modal.format(args.title, args.body);
  var obj = $(res);
  var deny = $(
    '<button type="button" class="btn btn-danger" data-dismiss="modal">Mark Incorrect</button>'
  );
  var confirm = $(
    '<button type="button" class="btn btn-success" data-dismiss="modal">Mark Correct</button>'
  );
  obj.find(".modal-footer").append(deny);
  obj.find(".modal-footer").append(confirm);

  $("main").append(obj);

  $(obj).on("hidden.bs.modal", function(e) {
    $(this).modal("dispose");
  });

  $(confirm).click(function() {
    args.success();
  });

  $(deny).click(function() {
    args.error();
  });

  obj.modal("show");

  return obj;
}

// TODO: Replace this with CTFd JS library
$(document).ready(function() {
  $(".grade-submission").click(function() {
    var elem = $(this)
      .parent()
      .parent();
    var chal = elem.find(".chal").attr("id");
    var chal_name = elem
      .find(".chal")
      .text()
      .trim();
    var team = elem.find(".team").attr("id");
    var team_name = elem
      .find(".team")
      .text()
      .trim();
    var description = elem
      .find(".desc")
      .text()
      .trim();
    var submission = elem.find(".submission").attr("id");
    var prompt_content = elem
      .find(".prompt")
      .text()
      .trim();
    var text_content = elem
      .find(".flag")
      .text()
      .trim();
    var key_id = elem.find(".flag").attr("id");

    var td_row = $(this)
      .parent()
      .parent();

    ezgrade({
      title: "Submission",
      body: " {0}'s submission for {1}:<strong> <br> Challenge Description: <br> </strong> {2} <strong> <br> Prompt: <br> </strong> {2} <strong> <br> Generation: </strong> <br> {3}".format(
        "<strong>" + htmlentities(team_name) + "</strong>",
        "<strong>" + htmlentities(chal_name) + "</strong>",
        "<pre>" + htmlentities(description) + "</pre>",
        "<pre>" + htmlentities(prompt_content) + "</pre>",
        "<pre>" + htmlentities(text_content) + "</pre>"
      ),
      success: function() {
        CTFd.fetch("/admin/verify_submissions/" + key_id + "/solve", {
          method: "POST"
        })
          .then(function(response) {
            return response.json();
          })
          .then(function(response) {
            if (response.success) {
              td_row.remove();
            }
          });
      },
      error: function() {
        CTFd.fetch("/admin/verify_submissions/" + key_id + "/fail", {
          method: "POST"
        })
          .then(function(response) {
            return response.json();
          })
          .then(function(response) {
            if (response.success) {
              td_row.remove();
            }
          });
      }
    });
  });
});
