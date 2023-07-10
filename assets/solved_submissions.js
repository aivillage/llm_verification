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

  $("main").append(obj);

  $(obj).on("hidden.bs.modal", function(e) {
    $(this).modal("dispose");
  });

  obj.modal("show");

  return obj;
}

// TODO: Replace this with CTFd JS library
$(document).ready(function() {
  $(".view-submission").click(function() {
    var elem = $(this)
      .parent()
      .parent();
    var chal = elem.find(".chal").attr("id");
    var chal_name = elem
      .find(".chal")
      .text()
      .trim();
    var description = elem
      .find(".desc")
      .text()
      .trim();
    var team = elem.find(".team").attr("id");
    var team_name = elem
      .find(".team")
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

    ezgrade({
      title: "Submission",
      body: " {0}'s submission for {1}: <strong> <br> Description: <br> </strong> {2} <strong> <br> Prompt: <br> </strong> {3} <strong> <br> Text: </strong> <br> {4}".format(
        "<strong>" + htmlentities(team_name) + "</strong>",
        "<strong>" + htmlentities(chal_name) + "</strong>",
        "<pre>" + htmlentities(description) + "</pre>",
        "<pre>" + htmlentities(prompt_content) + "</pre>",
        "<pre>" + htmlentities(text_content) + "</pre>"
      )
    });
  });
});
