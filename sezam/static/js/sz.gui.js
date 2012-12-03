$(function() {
    $('#auth_tree').tree({
        autoOpen: 0,
        autoEscape: false,
        selectable: true
    });
});


// $('.authority-profile').click(
//     function(evt) {
//         var $this = $(evt.target);     
//         alert($this.parents('div').find('.authority-info'));
//         $this.parents('div').find('.authority-info').show();
//         return false;
// });

$(document).ready(function() {
    var showChar = 100;
    var ellipsestext = "...";
    var moretext = "more";
    var lesstext = "less";
    $('.more').each(function() {
        var content = $(this).html();
        if(content.length > showChar) {
            var c = content.substr(0, showChar);
            var h = content.substr(showChar-1, content.length - showChar);
            var html = c + '<span class="moreellipses">' + ellipsestext+ '&nbsp;</span><span class="morecontent"><span>' + h + '</span>&nbsp;&nbsp;<a href="" class="morelink">' + moretext + '</a></span>';
            $(this).html(html);
        }
    });
    
    $(".morelink").click(function(){
        if($(this).hasClass("less")) {
            $(this).removeClass("less");
            $(this).html(moretext);
        } else {
            $(this).addClass("less");
            $(this).html(lesstext);
        }
        $(this).parent().prev().toggle();
        $(this).prev().toggle();
        return false;
    });
});