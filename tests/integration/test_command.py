import re
import unittest
import pexpect


class CommandTestCase(unittest.TestCase):
    def setUp(self):
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/hello_world')
        debugger.expect('BugStalker greets')
        self.debugger = debugger

    def test_debugee_execute(self):
        """Debugee executing"""
        self.debugger.sendline('run')
        self.debugger.expect('Hello, world!')
        self.debugger.expect('bye!')

    def test_function_breakpoint(self):
        """Stop debugee at function by its name"""
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('myprint("Hello, world!");')

        self.debugger.sendline('break myprint')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('continue')
        self.debugger.expect_exact('Hit breakpoint 2')
        self.debugger.sendline('continue')
        self.debugger.expect('Hello, world!')
        self.debugger.expect_exact('Hit breakpoint 2')
        self.debugger.sendline('continue')
        self.debugger.expect('bye!')

    def test_line_breakpoint(self):
        """Stop debugee at line by its number"""
        self.debugger.sendline('break hello_world.rs:15')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('15     println!("{}", s)')
        self.debugger.sendline('continue')
        self.debugger.expect('Hello, world!')
        self.debugger.expect_exact('15     println!("{}", s)')
        self.debugger.sendline('continue')
        self.debugger.expect('bye!')

    def test_multiple_breakpoints_set(self):
        """Sets multiple breakpoints at line"""
        self.debugger.sendline('break hello_world.rs:5')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('break hello_world.rs:9')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('Hit breakpoint 1 at')
        self.debugger.expect_exact('myprint("Hello, world!")')

        self.debugger.sendline('continue')
        self.debugger.expect_exact('Hello, world!')
        self.debugger.expect_exact('Hit breakpoint 2 at')
        self.debugger.expect_exact('myprint("bye!")')

        self.debugger.sendline('continue')
        self.debugger.expect('bye!')

    # maps 555555554000-55555555a000
    def test_address_breakpoint_set(self):
        """Sets breakpoints at address"""
        # determine address first
        self.debugger.sendline('break hello_world.rs:5')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('run')

        addr = ""
        for x in range(10):
            line = self.debugger.readline().decode("utf-8")
            result = re.search(r'Hit breakpoint 1 at .*0x(.*):', line)
            if result:
                addr = result.group(1)
                addr = "0x"+addr[:14]
                break

        self.assertNotEqual(addr, "")
        self.debugger.sendline('q')
        # respawn debugger and test address breakpoint
        self.debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/hello_world')
        self.debugger.expect('BugStalker greets')
        self.debugger.sendline('break ' + addr)
        self.debugger.expect_exact('New breakpoint')
        self.debugger.sendline('run')
        self.debugger.expect_exact('Hit breakpoint 1 at ')
        self.debugger.sendline('continue')
        self.debugger.expect('Hello, world!')
        self.debugger.expect('bye!')

    def test_write_register(self):
        """Register writes (by moving pc counter into program start)"""
        # determine program start and main ret addresses first
        self.debugger.sendline('break hello_world.rs:4')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('break hello_world.rs:10')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('run')

        start_addr = ""
        for x in range(10):
            line = self.debugger.readline().decode("utf-8")
            result = re.search(r'Hit breakpoint 1 at .*0x(.*):', line)
            if result:
                start_addr = result.group(1)
                start_addr = "0x"+start_addr[:14]
                break

        self.assertNotEqual(start_addr, "")
        self.debugger.sendline('continue')

        addr = ""
        for x in range(20):
            line = self.debugger.readline().decode("utf-8")
            result = re.search(r'Hit breakpoint 2 at .*0x(.*):', line)
            if result:
                addr = result.group(1)
                addr = "0x"+addr[:14]
                break

        self.assertNotEqual(addr, "")
        self.debugger.sendline('q')

        # assume that address of ret instruction at 1 byte offset
        addr_as_integer = int(addr, 16) + 1
        ret_addr = hex(addr_as_integer)

        # respawn debugger and move pc counter
        self.debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/hello_world')
        self.debugger.expect('BugStalker greets')
        self.debugger.sendline('break ' + ret_addr)
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect('Hello, world!')
        self.debugger.expect('bye!')

        self.debugger.sendline('register write rip ' + start_addr)

        self.debugger.sendline('continue')
        self.debugger.expect('Hello, world!')
        self.debugger.expect('bye!')

    @staticmethod
    def test_step_in():
        """Debugger step in command (move to next line)"""
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/calc -- 1 2 3 --description result')
        debugger.expect('BugStalker greets')
        debugger.sendline('break main.rs:10')
        debugger.expect('New breakpoint')

        debugger.sendline('run')
        debugger.expect('10     let s: i64')
        debugger.sendline('step')
        debugger.expect_exact('calc::sum3')
        debugger.expect_exact('25     let ab = sum2')
        debugger.sendline('step')
        debugger.expect_exact('calc::sum2')
        debugger.expect_exact('21     a + b')
        debugger.sendline('step')
        debugger.expect_exact('22 }')
        debugger.sendline('step')
        debugger.expect_exact('calc::sum3')
        debugger.expect_exact('26     sum2(ab, c)')
        debugger.sendline('step')
        debugger.expect_exact('calc::sum2')
        debugger.expect_exact('21     a + b')
        debugger.sendline('step')
        debugger.expect_exact('22 }')
        debugger.sendline('step')
        debugger.expect_exact('calc::sum3')
        debugger.expect_exact('27 }')
        debugger.sendline('step')
        debugger.expect_exact('calc::main')
        debugger.expect_exact('15     print(s, &args[5]);')

    def test_step_out(self):
        """Debugger step out command (move out from current function)"""
        self.debugger.sendline('break hello_world.rs:15')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('15     println!("{}", s)')
        self.debugger.sendline('stepout')
        self.debugger.expect_exact('7     sleep(Duration::from_secs(1));')

    def test_step_over(self):
        """Debugger step over command (move to next line without
        entering functions)"""
        self.debugger.sendline('break hello_world.rs:5')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('myprint("Hello, world!");')
        self.debugger.sendline('next')
        self.debugger.expect_exact('7     sleep(Duration::from_secs(1));')
        self.debugger.sendline('next')
        self.debugger.expect_exact('9     myprint("bye!")')
        self.debugger.sendline('next')
        self.debugger.expect_exact('10 }')

    def test_step_over_on_fn_decl(self):
        """Stop debugee at function declaration line"""
        self.debugger.sendline('break hello_world.rs:14')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect('Hit breakpoint 1 at')
        self.debugger.sendline('next')
        self.debugger.expect_exact('15     println!("{}", s)')

    def test_get_symbol(self):
        """Get debugee symbol"""
        self.debugger.sendline('symbol main')
        self.debugger.expect('__libc_start_main')
        self.debugger.expect('main - Text 0x[0-9A-F]{,16}')

    def test_backtrace(self):
        """Backtrace"""
        self.debugger.sendline('break hello_world.rs:15')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('15     println!("{}", s)')

        self.debugger.sendline('bt')
        self.debugger.expect_exact('myprint')
        self.debugger.expect_exact('hello_world::main')

    @staticmethod
    def test_args_for_executable():
        """Run debugee with arguments"""
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/calc -- 1 1 1 --description three')
        debugger.expect('BugStalker greets')
        debugger.sendline('r')
        debugger.expect_exact('three: 3')

    @staticmethod
    def test_read_value_u64():
        """Get program variable"""
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/calc -- 1 2 3 --description result')
        debugger.expect('BugStalker greets')
        debugger.sendline('break main.rs:15')
        debugger.expect('New breakpoint')

        debugger.sendline('run')
        debugger.expect_exact('15     print(s, &args[5]);')

        debugger.sendline('var locals')
        debugger.expect_exact('s = i64(6)')

    def test_function_breakpoint_remove(self):
        """Remove breakpoint at function by its name"""
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('break remove main')
        self.debugger.expect('Removed breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect('bye!')

    def test_line_breakpoint_remove(self):
        """Remove breakpoint at line by its number"""
        self.debugger.sendline('break hello_world.rs:15')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect_exact('15     println!("{}", s)')

        self.debugger.sendline('break remove hello_world.rs:15')
        self.debugger.expect('Removed breakpoint')

        self.debugger.sendline('continue')
        self.debugger.expect('bye!')

    def test_breakpoint_remove_by_number(self):
        """Remove breakpoint by its number"""
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('break remove 1')
        self.debugger.expect('Removed breakpoint')

        self.debugger.sendline('run')
        self.debugger.expect('bye!')

    def test_breakpoint_info(self):
        """View breakpoints list"""
        self.debugger.sendline('break hello_world.rs:9')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('break myprint')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('break hello_world.rs:7')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('break info')

        self.debugger.expect(r'- Breakpoint 1 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:9 ')
        self.debugger.expect(r'- Breakpoint 2 at .*0x[0-9A-F]{14,16}.*: .*\/rt\.rs:97')
        self.debugger.expect(r'- Breakpoint 3 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:5')
        self.debugger.expect(r'- Breakpoint 4 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:7')

        self.debugger.sendline('run')

        self.debugger.sendline('break info')

        self.debugger.expect(r'- Breakpoint 1 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:9 ')
        self.debugger.expect(r'- Breakpoint 2 at .*0x[0-9A-F]{14,16}.*: .*\/rt\.rs:97')
        self.debugger.expect(r'- Breakpoint 3 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:5')
        self.debugger.expect(r'- Breakpoint 4 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:7')

        self.debugger.sendline('break remove main')
        self.debugger.expect('Removed breakpoint')

        self.debugger.sendline('break info')
        self.debugger.expect(r'- Breakpoint 1 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:9 ')
        self.debugger.expect(r'- Breakpoint 2 at .*0x[0-9A-F]{14,16}.*: .*\/rt\.rs:97')
        self.debugger.expect(r'- Breakpoint 4 at .*0x[0-9A-F]{14,16}.*: .*\/hello_world\.rs.*:7')

    def test_debugee_restart(self):
        """Debugee process restart"""
        self.debugger.sendline('run')
        self.debugger.expect('Hello, world!')
        self.debugger.expect('bye!')
        self.debugger.sendline('run')
        self.debugger.expect('Restart a program?')
        self.debugger.sendline('y')
        self.debugger.expect('Hello, world!')
        self.debugger.expect('bye!')

    def test_debugee_restart_at_bp(self):
        """Debugee process restarting at breakpoint"""
        self.debugger.sendline('break hello_world.rs:9')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('run')
        self.debugger.expect('Hello, world!')
        self.debugger.sendline('run')
        self.debugger.expect('Restart a program?')
        self.debugger.sendline('y')
        self.debugger.expect('Hello, world!')
        self.debugger.sendline('continue')
        self.debugger.expect('bye!')

    def test_debugee_restart_at_end(self):
        """Debugee process restarting after debugee completing"""
        self.debugger.sendline('break hello_world.rs:9')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('run')
        self.debugger.expect_exact('Hello, world!')
        self.debugger.expect_exact('Hit breakpoint 1')
        self.debugger.sendline('continue')
        self.debugger.expect_exact('bye!')
        self.debugger.sendline('run')
        self.debugger.expect('Restart a program?')
        self.debugger.sendline('y')
        self.debugger.expect_exact('Hello, world!')
        self.debugger.expect_exact('Hit breakpoint 2')
        self.debugger.sendline('quit')

    @staticmethod
    def test_frame_switch():
        """Switch stack frame and assert argument values"""
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/calc -- 1 2 3 --description result')
        debugger.expect('BugStalker greets')
        debugger.sendline('break main.rs:21')
        debugger.expect_exact('New breakpoint 1')

        debugger.sendline('r')
        debugger.expect_exact('Hit breakpoint 1')

        debugger.sendline('arg all')
        debugger.expect_exact('a = i64(1)')
        debugger.expect_exact('b = i64(2)')

        debugger.sendline('frame switch 1')
        debugger.sendline('arg all')
        debugger.expect_exact('a = i64(1)')
        debugger.expect_exact('b = i64(2)')
        debugger.expect_exact('c = i64(3)')

    def test_disasm(self):
        """View function disassembled code"""
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')

        self.debugger.sendline('source asm')
        self.debugger.expect_exact('Assembler code for function hello_world::main')
        self.debugger.expect_exact('mov')

        self.debugger.sendline('break myprint')
        self.debugger.expect('New breakpoint')
        self.debugger.sendline('continue')

        self.debugger.sendline('source asm')
        self.debugger.expect_exact('Assembler code for function hello_world::myprint')
        self.debugger.expect_exact('mov')

    def test_source_fn(self):
        """View function source code"""
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')

        self.debugger.sendline('source fn')
        self.debugger.expect_exact('hello_world::main at')
        self.debugger.expect_exact('4 fn main() {')
        self.debugger.expect_exact('7     sleep(Duration::from_secs(1));')
        self.debugger.expect_exact('10 }')

    @staticmethod
    def test_source_fn_with_frame_switch():
        """Switch stack frame and assert argument values"""
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/calc -- 1 2 3 --description result')
        debugger.expect('BugStalker greets')
        debugger.sendline('break main.rs:21')
        debugger.expect_exact('New breakpoint 1')

        debugger.sendline('r')
        debugger.expect_exact('Hit breakpoint 1')

        debugger.sendline('source fn')
        debugger.expect_exact('fn sum2(a: i64, b: i64) -> i64 {')
        debugger.expect_exact('a + b')
        debugger.expect_exact('}')

        debugger.sendline('frame switch 1')
        debugger.sendline('source fn')
        debugger.expect_exact('fn sum3(a: i64, b: i64, c: i64) -> i64 {')
        debugger.expect_exact('let ab = sum2(a, b);')
        debugger.expect_exact('sum2(ab, c)')
        debugger.expect_exact('}')

        debugger.sendline('frame switch 2')
        debugger.sendline('source fn')
        debugger.expect_exact('fn main() {')
        debugger.expect_exact('let args: Vec<String> = env::args().collect();')
        debugger.expect_exact('let v1 = &args[1];')
        debugger.expect_exact('let v2 = &args[2];')
        debugger.expect_exact('}')

    def test_source_bounds(self):
        """View source code"""
        self.debugger.sendline('break main')
        self.debugger.expect('New breakpoint')

        self.debugger.sendline('run')

        self.debugger.sendline('source 4')
        self.debugger.expect_exact('1 use std::thread::sleep;')
        self.debugger.expect_exact('4 fn main() {')
        self.debugger.expect_exact('9     myprint("bye!")')

    @staticmethod
    def test_breakpoint_at_rust_panic():
        """Set breakpoint to rust panic handler and catch panics"""
        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/panic -- user')
        debugger.sendline('break rust_panic')
        debugger.expect('New breakpoint')
        debugger.sendline('run')
        debugger.expect_exact('then panic!')
        debugger.sendline('bt')
        debugger.expect('rust_panic')
        debugger.expect('panic::user_panic')
        debugger.sendline('continue')

        debugger = pexpect.spawn(
            './target/debug/bs -t none ./examples/target/debug/panic -- system')
        debugger.sendline('break rust_panic')
        debugger.expect('New breakpoint')
        debugger.sendline('run')
        debugger.expect('attempt to divide by zero')
        debugger.sendline('bt')
        debugger.expect('rust_panic')
        debugger.expect('panic::divided_by_zero')
