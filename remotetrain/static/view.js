$(function() {
	$("#form_controller input").change(
			function(e) {
				sendSingle(this.name, this.value, "/update_control");
			}
	);

	$("#form_camera input[type='radio']").change(
			function(e) {

				var json_data;

				if (this.value == "movie") {
					$("#shoot").val("movie");
					$("#shoot").text("Start Rec");

					json_data = {"method": "setShootMode", "params": ["movie"]};
					sendJson(json_data, "/camera_api");
				}
				else if (this.value == "still") {
					$("#shoot").val("still");
					$("#shoot").text("Capture");

					json_data = {"method": "setShootMode", "params": ["still"]};
					sendJson(json_data, "/camera_api");
				}
			}
	);

	$("#shoot").click(
			function(e) {

				var json_data;

				if (this.value == "movie") {
					$("#shoot").val("recording");
					$("#shoot").text("Now Recording");

					json_data = {"method": "startMovieRec", "params": []};	
					sendJson(json_data, "/camera_api");
				}
				else if (this.value == "recording") {
					$("#shoot").val("movie");
					$("#shoot").text("Start Rec");

					json_data = {"method": "stopMovieRec", "params": []};
					sendJson(json_data, "/camera_api");
				}
				else if (this.value == "still") {

					json_data = {"method": "actTakePicture", "params": []};
					sendJson(json_data, "/camera_api");
				}

				return false;
			}
	);

	initWebSocket();

	reset();

});


function reset() {
	if ( $("#form_controller")[0] ) {
		$('#form_controller input[type="range"]').val(0);
		$('#form_controller input[type="radio"][value="0"]').val([0]);
		sendControllerForm();
	}
	
	if ( $("#form_camera")[0] ) {
		$('#form_camera input[type="radio"][value="movie"]').val(["movie"]);
		sendJson({"method": "setShootMode", "params": ["movie"]}, "/camera_api");	
	}
}

function sendSingle(name, value, url) {
	var json_data　= {};
	json_data[name] = value;

	$.ajax({
		type : "POST",
		url: url,
		dataType: "json",
		contentType: "application/json",
		success: recvData,
		data: JSON.stringify(json_data)
	})
	.done(function(data, textStatus, jqXHR ){
		console.log("done");
		console.log(data);
	})
	.fail(function(jqXHR, textStatus, errorThrown){
		console.log("failed");
	});
}

function sendJson(json_data, url) {

	$.ajax({
		type : "POST",
		url: url,
		dataType: "json",
		contentType: "application/json",
		success: recvData,
		data: JSON.stringify(json_data)
	})
	.done(function(data, textStatus, jqXHR ){
		console.log("done");
		console.log(data);
	})
	.fail(function(jqXHR, textStatus, errorThrown){
		console.log("failed");
	});
}


function sendControllerForm() {

	var json_data　= {};
	var elements;

	elements = $('#form_controller input[type="range"]').get()
	for (var i=0 ; i < elements.length ; ++i) {
		json_data[elements[i].name] = elements[i].value
	}
	elements = $('#form_controller input[type="radio"]:checked').get()
	for (var i=0 ; i < elements.length ; ++i) {
		json_data[elements[i].name] = elements[i].value
	}

	var r=JSON.stringify(json_data);

	$.ajax({
		type : "POST",
		url: "/update_control",		
		dataType: "json",
		contentType: "application/json",
		success: recvData,
		data: JSON.stringify(json_data)
	})
	.done(function(data, textStatus, jqXHR ){
		console.log("done");
		console.log(data);
	})
	.fail(function(jqXHR, textStatus, errorThrown){
		console.log("failed");
	});

}


function recvData(data) {
	$("#recv_data").text(JSON.stringify(data));
}





function initWebSocket() {

	var socket = null;
	var isopen = false;
	var current = 0;
	var past = 0;
	var hostname = window.location.hostname;

	socket = new WebSocket("ws://" + hostname + ":9000");
	socket.binaryType = "arraybuffer";

	socket.onopen = function() {
		console.log("Connected.");
		console.log("Current Dir: %s", window.location.pathname);
		isopen = true;
	}

	socket.onmessage = function(e) {
		showMessage(e)
		showImage(e)

		current = new Date().getTime();
		console.log("message received: " + e.data);
		console.log(current - past + " ms")
		past = current;
	}

	socket.onclose = function(e) {
		console.log("Connection closed.");
		socket = null;
		isopen = false;
	}

	function sendText(text) {
        if (isopen) {
           socket.send(text);
           console.log(text);
        } else {
           console.log("Connection not opened.")
        }
	};
}

function showMessage(e) {
	$("#jpeg_name").text(e.data);
}

function showImage(e) {        	  
	var img = new Image();
	img.onload = function() {
		var context = $("#liveview")[0].getContext('2d');
		context.drawImage(img, 0, 0);	 
	}
	img.src = e.data;
}
