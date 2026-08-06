<?php

declare(strict_types=1);

use PHPUnit\Framework\TestCase;

final class CalculadoraTest extends TestCase
{
    public function testSoma(): void
    {
        self::assertSame(5, 2 + 3);
    }
}
