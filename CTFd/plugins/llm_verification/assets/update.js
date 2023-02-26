(function () {
    var t = setInterval(function () {
        if (window.jQuery || typeof CTFd === 'object') {
            if (CTFd.lib.$) {
                $ = CTFd.lib.$;
            }

            $(document).ready(function () {
                $('[data-toggle="tooltip"]').tooltip();
            });
            clearInterval(t);
        }
    }, 100);
})();
