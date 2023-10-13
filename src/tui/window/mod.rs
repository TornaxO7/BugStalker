use crate::console;
use crate::debugger::command::{Continue, Run, StepInto, StepOut, StepOver};
use crate::debugger::Debugger;
use crate::tui::window::app::AppWindow;
use crate::tui::window::message::Exchanger;
use crate::tui::{context, AppState, DebugeeStreamBuffer, Event, Handle};
use crate::util::DebugeeOutReader;
use crossterm::event::{DisableMouseCapture, KeyCode, KeyEvent, KeyModifiers};
use crossterm::terminal::{disable_raw_mode, LeaveAlternateScreen};
use std::io::StdoutLock;
use std::sync::mpsc::Receiver;
use tui::backend::CrosstermBackend;
use tui::layout::Rect;
use tui::{Frame, Terminal};

mod app;
mod general;
mod message;
mod specialized;

#[derive(Default, Clone, Copy)]
pub struct RenderOpts {
    pub in_focus: bool,
}

pub trait TuiComponent {
    fn render(
        &self,
        frame: &mut Frame<CrosstermBackend<StdoutLock>>,
        rect: Rect,
        opts: RenderOpts,
        debugger: &mut Debugger,
    );
    fn handle_user_event(&mut self, e: KeyEvent);
    fn update(&mut self, _debugger: &mut Debugger) -> anyhow::Result<()> {
        Ok(())
    }
    fn name(&self) -> &'static str;
}

macro_rules! try_else_alert {
    ($e: expr) => {
        if let Err(e) = $e {
            context::Context::current().set_alert(format!("An error occurred: {e}").into());
        }
    };
}

pub(super) fn run(
    mut terminal: Terminal<CrosstermBackend<StdoutLock>>,
    mut debugger: Debugger,
    event_chan: Receiver<Event<KeyEvent>>,
    stream_buff: DebugeeStreamBuffer,
    debugee_out: DebugeeOutReader,
    debugee_err: DebugeeOutReader,
    handles: Vec<Handle>,
) -> anyhow::Result<()> {
    let mut app_window = AppWindow::new(stream_buff);

    loop {
        terminal.draw(|frame| {
            let rect = frame.size();
            app_window.render(frame, rect, RenderOpts::default(), &mut debugger);
        })?;

        let ctx = context::Context::current();
        if ctx.assert_state(AppState::UserInput) {
            match event_chan.recv()? {
                Event::Input(e) => app_window.handle_user_event(e),
                Event::Tick => {}
            }
        } else {
            match event_chan.recv()? {
                Event::Input(e) => match e {
                    KeyEvent {
                        code: KeyCode::Char('c'),
                        modifiers,
                        ..
                    } => {
                        if modifiers.contains(KeyModifiers::ALT) {
                            drop(handles);

                            disable_raw_mode()?;
                            crossterm::execute!(
                                terminal.backend_mut(),
                                LeaveAlternateScreen,
                                DisableMouseCapture
                            )?;
                            crossterm::execute!(terminal.backend_mut(), crossterm::cursor::Show)?;
                            crossterm::execute!(
                                terminal.backend_mut(),
                                crossterm::cursor::RestorePosition
                            )?;

                            drop(terminal);

                            let app = console::AppBuilder::new(debugee_out, debugee_err)
                                .build(debugger)
                                .expect("build application fail");
                            app.run().expect("run application fail");
                            return Ok(());
                        } else {
                            ctx.change_state(AppState::DebugeeRun);
                            try_else_alert!(Continue::new(&mut debugger).handle());
                        }
                    }
                    KeyEvent {
                        code: KeyCode::Char('r'),
                        ..
                    } => {
                        ctx.change_state(AppState::DebugeeRun);
                        try_else_alert!(Run::new(&mut debugger).start());
                    }
                    KeyEvent {
                        code: KeyCode::Char('q'),
                        ..
                    } => {
                        disable_raw_mode()?;
                        crossterm::execute!(
                            terminal.backend_mut(),
                            LeaveAlternateScreen,
                            DisableMouseCapture,
                        )?;
                        terminal.show_cursor()?;
                        return Ok(());
                    }
                    KeyEvent {
                        code: KeyCode::F(8),
                        ..
                    } => {
                        try_else_alert!(StepOver::new(&mut debugger).handle());
                    }
                    KeyEvent {
                        code: KeyCode::F(7),
                        ..
                    } => {
                        try_else_alert!(StepInto::new(&mut debugger).handle());
                    }
                    KeyEvent {
                        code: KeyCode::F(6),
                        ..
                    } => {
                        try_else_alert!(StepOut::new(&mut debugger).handle());
                    }
                    _ => {
                        app_window.handle_user_event(e);
                    }
                },
                Event::Tick => {}
            }
        }

        while !Exchanger::current().is_empty() {
            if let Err(e) = app_window.update(&mut debugger) {
                context::Context::current().set_alert(format!("An error occurred: {e}").into());
                Exchanger::current().clear();
                break;
            }
        }
    }
}
