// 获取cookie
function getCookie(name) {
   var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
   return r ? r[1] : undefined;
}

// 用来保存前一个code_id
var imageCodeId = "";

// 随机生成 code_id
function generateUUID() {
    var d = new Date().getTime();
    if(window.performance && typeof window.performance.now === "function"){
        d += performance.now(); //use high-precision timer if available
    }
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
    return uuid;
}

//验证码
function generateImageCode() {
    var pic_id = generateUUID()
    $(".image-code img").attr("src", "/api/check_login?pre="+imageCodeId+"&cur="+pic_id)
    imageCodeId = pic_id
}


// 发送手机验证码
function sendSMSCode() {
    $(".phonecode-a").removeAttr("onclick");
    var mobile = $("#mobile").val()
    if(!mobile){
        $("#mobile-err span").html("请填写正确的手机号！");
        $("#mobile-err").show();
        $(".phonecode-a").attr("onclick", "sendSMSCode();");
        return;
    }
    var image_code = $("#imagecode").val()
        if(!image_code){
             $("#image-code-err span").html("请填写验证码！");
             $("#image-code-err").show();
             $(".phonecode-a").attr("onclick", "sendSMSCode();");
             return;
        }
    var data = {mobile:mobile, pic_code:image_code, pic_code_id:imageCodeId}
    $.ajax({
        url:"/api/smscode",
        type:"POST",
        headers:{
            "X-XSRFTOKEN": getCookie("_xsrf"),
        },
        dataType:"json",
        contentType: "application/json",
        data:JSON.stringify(data),
        success: function (data) {
            if("0" == data.errode){
                var duration = 60
                var time_obj = setInterval(function () {
                    duration = duration - 1;
                    $(".phonecode-a").html(duration+"秒")
                    if(1 == duration){
                        clearInterval(time_obj)
                        $(".phonecode-a").html("获取验证码")
                        $(".phonecode-a").attr("onclick", "sendSMSCode();")
                    }
                }, 1000, 60)
            }else {
                $("#image-code-err span").html(data.errmsg);
                $("#image-code-err").show();
                $(".phonecode-a").attr("onclick", "sendSMSCode();")
                if (data.errcode == "4002" || data.errcode == "4004") {
                    generateImageCode();
                }
            }
        }
    })
}