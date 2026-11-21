import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import broadway_dedup as bd  # noqa: E402

COLOR = [0, 0, 0, 0, 0]


def color(node):
    return [bd.COLOR, node, *COLOR]


def texture(node, texture_id):
    return [bd.TEXTURE, node, 0, 0, 0, 0, texture_id]


def container(node, *children):
    return [bd.CONTAINER, node, len(children)] + [word for child in children for word in child]


def reuse(node):
    return [bd.REUSE, node]


def request(kind, *words, serial=1):
    body = struct.pack(f"={len(words)}I", *words)
    return bd.HEADER.pack(bd.HEADER.size + len(body), serial, kind) + body


def test_frame_without_repeats_is_untouched():
    surface = bd.Surface()
    first = container(1, color(2), color(3))
    assert surface.rewrite(first) is first
    second = container(4, reuse(2), reuse(3))
    assert surface.rewrite(second) is second


def test_second_reuse_becomes_a_copy_with_a_new_id():
    surface = bd.Surface()
    surface.rewrite(container(1, color(2)))
    out = surface.rewrite(container(3, reuse(2), reuse(2)))
    assert out == container(3, reuse(2), color(bd.FIRST_COPY_ID))
    # The next frame may reuse the same node twice again.
    out = surface.rewrite(container(4, reuse(2), reuse(2)))
    assert out == container(4, reuse(2), color(bd.FIRST_COPY_ID + 1))


def test_reuse_of_a_node_below_a_reused_node_becomes_a_copy():
    surface = bd.Surface()
    surface.rewrite(container(1, container(2, color(3)), color(4)))
    out = surface.rewrite(container(5, reuse(2), reuse(3)))
    assert out == container(5, reuse(2), color(bd.FIRST_COPY_ID))


def test_copy_includes_children():
    surface = bd.Surface()
    surface.rewrite(container(1, container(2, color(3))))
    out = surface.rewrite(container(4, reuse(2), reuse(2)))
    first = bd.FIRST_COPY_ID
    assert out == container(4, reuse(2), container(first, color(first + 1)))


def test_requests_are_split_and_resized():
    requests = bd.Requests()
    flush = request(1)
    first = request(bd.REQUEST_SET_NODES, 7, *container(1, color(2)))
    stream = flush + first
    assert requests.feed(stream[:5]) == b""
    assert requests.feed(stream[5:]) == stream
    out = requests.feed(request(bd.REQUEST_SET_NODES, 7, *container(3, reuse(2), reuse(2)), serial=2))
    assert out == request(bd.REQUEST_SET_NODES, 7,
                          *container(3, reuse(2), color(bd.FIRST_COPY_ID)), serial=2)
    assert requests.copies() == 1


def test_texture_release_waits_while_a_node_can_be_copied():
    requests = bd.Requests()
    release = request(bd.REQUEST_RELEASE_TEXTURE, 9, serial=2)
    requests.feed(request(bd.REQUEST_SET_NODES, 7, *container(1, texture(2, 9))))
    assert requests.feed(release) == b""
    unused = request(bd.REQUEST_RELEASE_TEXTURE, 8, serial=3)
    assert requests.feed(unused) == unused
    frame = request(bd.REQUEST_SET_NODES, 7, *container(3, color(4)), serial=4)
    assert requests.feed(frame) == frame + request(bd.REQUEST_RELEASE_TEXTURE, 9, serial=4)


def test_unknown_node_type_forwards_unchanged():
    requests = bd.Requests()
    odd = request(bd.REQUEST_SET_NODES, 7, 99, 1)
    assert requests.feed(odd) == odd
    later = request(bd.REQUEST_SET_NODES, 7, *container(3, reuse(2), reuse(2)))
    assert requests.feed(later) == later
