if (CTFd._internal.challenge) {
    var challenge = CTFd._internal.challenge;
} else {
    var challenge = window.challenge;
}

if (CTFd.lib.$) {
    $ = CTFd.lib.$;
}

$(document).ready(function(){
    $('[data-toggle="tooltip"]').tooltip();
});
