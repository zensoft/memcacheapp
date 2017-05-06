import telnetlib
import re
import datetime

HOST = "172.17.0.2"
PORT = 11211


class MemHelper:

    NEW_LINE = b"\n"
    SLABS_PATTERN = "STAT items:(?P<slab>\d+):number (?P<count>\d+)"
    ITEM_PATTERN = "ITEM (?P<key>[\w\-]*) \[(?P<ignored>\d+) b; (?P<time_stamp>\d+) s\]"

    def __init__(self, host, port):
        self.port = port
        self.host = host
        tn = self._connect()
        print("Polaczono z: {0} {1}".format(host, port))
        slabs = self._get_stats_slabs(tn)
        all_items = [("Klucz", "Data wygasniecia", "Wartosc")]
        for data in slabs:
            slab, count = self._extract_slab_count(data)
            cache_dump = self._get_cache_dump(tn, slab, count)
            all_items += self._parse_items(tn, cache_dump)

        all_items.sort()
        table = [(str(idx), it[0], it[1], it[2]) for idx, it in enumerate(all_items)]
        self.print_table(table)
        self._close(tn)

    def _get_value_for_key(self, tn, key):
        cmd = "get {0}".format(key)
        tn.write(cmd.encode("utf8") + self.NEW_LINE)
        res = tn.read_until(b"END").split(b"\r\n")
        if len(res) > 2:
            res = res[2]
            if self._is_binary_data(res):
                val = str(int.from_bytes(res, byteorder="big"))
                if len(val) > 13:
                    return res.decode("utf-8", errors="replace").replace("\n", "")[:40]# 40 bo czemu nie?
                else:
                    return val
            else:
                return res.decode("utf-8")
        else:
            return "No value for key"

    def _is_binary_data(self, data):
        try:
            data.decode("utf-8")
            return False
        except:
            return True

    def _connect(self):
        return telnetlib.Telnet(host=self.host, port=self.port)

    def _close(self, tn):
        tn.write(b"exit\n")
        tn.close()

    def _get_stats_slabs(self, tn):
        tn.write("stats items".encode("utf8") + self.NEW_LINE)
        res = tn.read_until(b"END").decode("utf8").split("\n")
        res = [line for line in res if re.match(self.SLABS_PATTERN, line)] # filter only items count, skip additional info
        return res

    def _extract_slab_count(self, data):
        pa = re.match(self.SLABS_PATTERN, data)
        return pa.group("slab"), pa.group("count")

    def _get_cache_dump(self, tn, slab, count):
        cmd = "stats cachedump {0} {1}".format(slab, count)
        tn.write(cmd.encode("utf8") + self.NEW_LINE)
        res = tn.read_until(b"END").decode("utf8").split("\n")[1:-1] #skip firs and last
        res = [l.strip() for l in res]
        return res

    def _parse_items(self, tn, cache_dump):
        items = []
        for item in cache_dump:
            pa = re.match(self.ITEM_PATTERN, item)
            if pa:
                key = pa.group("key")
                time_stamp = pa.group("time_stamp")
                time_stamp = datetime.datetime.fromtimestamp(int(time_stamp)).strftime('%Y-%m-%d %H:%M:%S')
                items.append((key, time_stamp, self._get_value_for_key(tn, key)))
            else:
                print("Skipped " + item)
        return items

    def print_table(self, table):
        col_width = [max(len(x) for x in col) for col in zip(*table)]
        for line in table:
            print("| " + " | ".join("{:{}}".format(x, col_width[i])
                                    for i, x in enumerate(line)) + " |")


def main():
    MemHelper(HOST, PORT)

if __name__ == "__main__":
    main()