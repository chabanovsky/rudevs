var markFalseId = "#mark-false";

$(document).ready(function() {
    $(markFalseId).click(function(event){
        event.preventDefault();
        href = event.target.href;
        loadHelper(href, function(data){
            alert("Statement was marked. Current status: " + data.false_assumption);
            if (document.referrer != document.URL)
                window.location.href = document.referrer;
            else 
                window.location.href = "/";
        }, function(){
            alert("Cannot send mark false request.");
        })

        return false;
    });
})