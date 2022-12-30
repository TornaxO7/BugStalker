use bugstalker::console::AppBuilder;
use bugstalker::cui;
use bugstalker::debugger::rust;
use clap::{arg, Parser};
use nix::libc::pid_t;
use nix::sys;
use nix::sys::personality::Persona;
use nix::unistd::Pid;
use std::os::unix::prelude::CommandExt;
use std::path::PathBuf;
use std::process::Stdio;

#[derive(Parser, Debug, Clone)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Debugger interface type
    #[arg(long, default_value_t = String::from("console"))]
    ui: String,

    debugee: String,

    /// Path to rust stdlib
    #[clap(short, long)]
    std_lib_path: Option<String>,
}

fn main() {
    let args = Args::parse();
    let debugee = &args.debugee;

    rust::Environment::init(args.std_lib_path.map(PathBuf::from));

    let mut debugee_cmd = std::process::Command::new(debugee);
    if args.ui.as_str() == "cui" {
        debugee_cmd.stdout(Stdio::piped());
        debugee_cmd.stderr(Stdio::piped());
    }

    unsafe {
        debugee_cmd.pre_exec(move || {
            sys::personality::set(Persona::ADDR_NO_RANDOMIZE)?;
            sys::ptrace::traceme()?;
            Ok(())
        });
    }
    let mut handle = debugee_cmd.spawn().expect("execute debugee fail");
    let pid = handle.id() as pid_t;

    println!("Child pid {:?}", pid);

    match args.ui.as_str() {
        "cui" => {
            let app = cui::AppBuilder::new(
                handle.stdout.take().expect("take debugee stdout fail"),
                handle.stderr.take().expect("take debugee stderr fail"),
            )
            .build(debugee, Pid::from_raw(pid))
            .expect("prepare application fail");
            app.run().expect("run application fail");
        }
        _ => {
            let app = AppBuilder::new()
                .build(debugee, Pid::from_raw(pid))
                .expect("prepare application fail");
            app.run().expect("run application fail");
        }
    }
}
