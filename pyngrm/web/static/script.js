$(document).ready(function() {
    document.session = $('#session').val();
    var loc = window.location;
    $(".button").on("click", function() {
        $.ajax({url: loc.pathname + loc.search, type: 'POST'});
        setTimeout(requestBoard, 100);
    });
    setTimeout(requestBoard, 100);

    $("#slider").on("change", function() {
        $("body").toggleClass("night");
    })
});


function requestBoard() {
    var session = document.session;
    $.ajax({
        url: "/board/status/" + session,
        success: function(result){
            board = result["board"];
            delete result["board"];
            $("#board").html(board);

            if (!jQuery.isEmptyObject(result)) {
                console.log(result);
                $("#extra").append("<div>"+ JSON.stringify(result) + "</div>");
            }

            var timeout = 0;
            if (result["complete"] === true) {
                console.log("Complete!")
                // timeout = 5000;  // reduce status checks
            }
            else {
                setTimeout(requestBoard, timeout);
            }
        },
        error: function (xhr, ajaxOptions, thrownError) {
            console.error(xhr, ajaxOptions, thrownError);
        }
    });
}
