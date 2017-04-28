var markFalseClass = ".mark-false";
var reviewClass = ".review";
var extendClass = ".extend";

$(document).ready(function() {
    $(markFalseClass).click(function(event){
        event.preventDefault();
        href = event.target.href;

        loadHelper(href, function(data){
            window.location.reload();
        }, function(){
            alert("Cannot send mark false request.");
        })

        return false;
    });

    $(reviewClass).click(function(event){
        event.preventDefault();
        href = event.target.href;

        loadHelper(href, function(data){
            window.location.reload();
        }, function(){
            alert("Cannot send review request.");
        })

        return false;
    });

    $(extendClass).click(function(event){
        event.preventDefault();
        href = event.target.href;

        loadHelper(href, function(data){
            window.location.reload();
        }, function(){
            alert("Cannot send extend request.");
        })

        return false;
    });    
    
})