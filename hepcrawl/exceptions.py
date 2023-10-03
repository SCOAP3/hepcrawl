class UnknownLicense(Exception):
    def __init__(self, license):
        super(UnknownLicense, self).__init__("Unknown license type: {0}".format(license))
