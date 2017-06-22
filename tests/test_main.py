"""Test main utilities"""
from collections import defaultdict
import builtins

from rever.activity import Activity
from rever.main import (env_main, compute_activities_completed,
                        compute_activities_to_run)


def test_source_rc(gitrepo):
    with open('rever.xsh', 'w') as f:
        f.write('$YOU_DONT = "always"\n')
    env_main(args=['x.y.z'])
    assert builtins.__xonsh_env__['YOU_DONT'] == 'always'
    del builtins.__xonsh_env__['YOU_DONT']


def test_alt_source_rc(gitrepo):
    with open('rc.xsh', 'w') as f:
        f.write('$YOU_DO = "never"\n')
    env_main(args=['--rc=rc.xsh', 'x.y.z'])
    assert builtins.__xonsh_env__['YOU_DO'] == 'never'
    del builtins.__xonsh_env__['YOU_DO']


def test_activities_from_rc(gitrepo):
    with open('rever.xsh', 'w') as f:
        f.write('$ACTIVITIES = {"a", "b", "c"}\n')
    env = builtins.__xonsh_env__
    env['ACTIVITY_DAG'] = defaultdict(Activity)
    env_main(args=['x.y.z'])
    assert env['ACTIVITIES'] == {"a", "b", "c"}


def test_activities_from_cli(gitrepo):
    with open('rever.xsh', 'w') as f:
        f.write('$ACTIVITIES = {"a", "b", "c"}\n')
    env = builtins.__xonsh_env__
    env['ACTIVITY_DAG'] = defaultdict(Activity)
    env_main(args=['-a', 'e,f,g', 'x.y.z'])
    assert env['ACTIVITIES'] == {"e", "f", "g"}


def test_dont_redo_deps(gitrepo):
    # This test runs an activity a, then runs an activity b that depends on a
    # During the second run, a should not be rerun since it was already
    # run the first time.
    env = builtins.__xonsh_env__
    dag = env['ACTIVITY_DAG']
    a = dag['a'] = Activity(name='a')
    b = dag['b'] = Activity(name='b', deps={'a'})
    # run the first time
    env_main(args=['--activities', 'a', 'x.y.z'])
    done = compute_activities_completed()
    assert done == {'a'}
    # test what we we need to run if we wanted to run b
    path, already_done = compute_activities_to_run(activities={'b'})
    assert path == ['b']
    assert already_done == ['a']
    # run for the second time
    env_main(args=['--activities', 'b', 'x.y.z'])
    done = compute_activities_completed()
    assert done == {'a', 'b'}
    # make sure a and b were each run exactly once
    entries = env['LOGGER'].load()
    a_ends = [e for e in entries if e['activity'] == 'a' and
                                    e['category'] == 'activity-end']
    assert len(a_ends) == 1
    b_ends = [e for e in entries if e['activity'] == 'b' and
                                    e['category'] == 'activity-end']
    assert len(b_ends) == 1


def test_redo_deps_if_reverted(gitrepo):
    # This test runs an activity a, undoes a, then runs an activity b that depends on a
    # During the last run, a should not be rerun since it was already
    # run the first time.
    env = builtins.__xonsh_env__
    dag = env['ACTIVITY_DAG']
    a = dag['a'] = Activity(name='a')
    b = dag['b'] = Activity(name='b', deps={'a'})
    # run the first time
    env_main(args=['--activities', 'a', 'x.y.z'])
    done = compute_activities_completed()
    assert done == {'a'}
    # undo a
    env_main(args=['--undo', 'a', 'x.y.z'])
    done = compute_activities_completed()
    assert done == set()
    # test what we we need to run if we wanted to run b
    path, already_done = compute_activities_to_run(activities={'b'})
    assert path == ['a', 'b']
    assert already_done == []
    # run for the second time
    env_main(args=['--activities', 'b', 'x.y.z'])
    done = compute_activities_completed()
    assert done == {'a', 'b'}
    # make sure a and b were each run exactly once
    entries = env['LOGGER'].load()
    a_ends = [e for e in entries if e['activity'] == 'a' and
                                    e['category'] == 'activity-end']
    assert len(a_ends) == 2
    b_ends = [e for e in entries if e['activity'] == 'b' and
                                    e['category'] == 'activity-end']
    assert len(b_ends) == 1