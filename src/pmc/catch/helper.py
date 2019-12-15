class class_or_instancemethod(classmethod):
    """
    USAGE
        class ClassName:
            @class_or_instancemethod
            def methodA(self_or_cls):
                if class_or_instancemethod.is_class(self_or_cls):
                    # act on self_or_cls as on Class (aka cls)
                    pass
                else:
                    # act on self_or_cls as on instance (aka self)
                    pass

            @class_or_instancemethod
            def methodB(self_or_cls):
                self_or_cls.methodX()
                self_or_cls.propertyX

    NOTES
        methodA() discriminate (does different action based on `self_or_cls`
        being Class or instance of Class

        methodB() does not discriminate (differentiate) and acts
        on `self_or_cls` being Class or instance of Class
        based on context automatically, just be sure that
        your class has methodX and propertyX available
        for Class as well as for an instance of a Class.
    """

    def __get__(self, instance, type_):
        dunder_get = super().__get__ if instance is None else self.__func__.__get__
        return dunder_get(instance, type_)

    @staticmethod
    def is_class(self_or_cls) -> bool:
        return isinstance(self_or_cls, type)

    @staticmethod
    def is_instance(self_or_cls) -> bool:
        return not isinstance(self_or_cls, type)
