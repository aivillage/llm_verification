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
    '<a href="/admin/llm_submissions/solved?challenge_id={0}">Solutions</a>'.format(args.id)
  );
  var confirm = $(
    '<a href="/admin/llm_submissions/all_generations?challenge_id={0}">Generations</a>'.format(args.id)
  );
  var award = $(
    '<a href="/admin/llm_submissions/pending?challenge_id={0}">Grade</a>'.format(args.id)
  );

  obj.find(".modal-footer").append(deny);
  obj.find(".modal-footer").append(confirm);
  obj.find(".modal-footer").append(award);

  $("main").append(obj);

  $(obj).on("hidden.bs.modal", function(e) {
    $(this).modal("dispose");
  });

  obj.modal("show");

  return obj;
}

// TODO: Replace this with CTFd JS library
$(document).ready(function() {
  $(".view-challenge").click(function() {
    var elem = $(this)
      .parent()
      .parent();
    var chal_id = elem.find(".chal").attr("id");
    var chal_name = elem
      .find(".name")
      .text()
      .trim();
    var description = elem
      .find(".desc")
      .text()
      .trim();
    var preprompt = elem
      .find(".desc")
      .text()
      .trim();

    ezgrade({
      title: "Challenge" + " " + chal_name,
      body: "<strong> <br> Description: <br> </strong> {0} <strong> <br> PrePrompt: <br> </strong> {1} <strong>".format(
        "<pre>" + htmlentities(description) + "</pre>",
        "<pre>" + htmlentities(preprompt) + "</pre>"
      ),
      id: chal_id,
    });
  });
});
