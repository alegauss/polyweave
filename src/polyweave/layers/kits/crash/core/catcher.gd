extends Logger
## Every error the engine raises, handed to the crash kit's log with the script and line
## it came from (§PW361). A script error names them itself; an error a script pushes is
## named by the engine's own source, so the place is the first script frame of its
## backtrace instead.

var log: Node


func _init(into: Node) -> void:
	log = into


func _log_error(function: String, file: String, line: int, code: String, rationale: String,
		_editor_notify: bool, error_type: int, script_backtraces: Array[ScriptBacktrace]) -> void:
	var script := file
	var at := line
	if not file.begins_with("res://"):
		for trace in script_backtraces:
			if trace.get_frame_count() > 0:
				script = trace.get_frame_file(0)
				at = trace.get_frame_line(0)
				break
	log.caught.call_deferred({"said": code if rationale == "" else "%s: %s" % [code, rationale],
		"script": script, "line": at, "function": function,
		"kind": ["error", "warning", "script", "shader"][clampi(error_type, 0, 3)]})


func _log_message(_message: String, _error: bool) -> void:
	pass
