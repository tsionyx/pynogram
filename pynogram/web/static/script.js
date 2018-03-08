$(document).ready(function() {
    document.board_id = $('#board_id').val();
    document.board_mode = $('#board_mode').val();
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
    var board_id = document.board_id;
    var board_mode = document.board_mode;
    $.ajax({
        url: "/board/status/" + board_mode + '/' + board_id,
        success: function(result){
            board = result["board"];
            delete result["board"];
            $("#board").html(board);

            if (!jQuery.isEmptyObject(result)) {
                console.log(result);
                // $("#extra").append("<div>"+ JSON.stringify(result) + "</div>");
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
